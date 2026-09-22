"""MicroBadges: a topic's ten bundles of practice, and the retries after a fail.

A MicroBadge is earned when every item still in it is done. Nothing here takes
one back: ``earned_at`` goes from empty to set exactly once, so a student who
unticks an item, or whose teacher adds work to a bundle they have already
finished, keeps what they earned.

The order 1 to 10 is a suggestion with target dates, not a lock. Any MicroBadge
can be earned at any time; the student's page simply leads with the lowest one
still to do. A lock would let one broken item stop a topic dead.
"""
from datetime import timedelta

from django.utils import timezone

from .. import constants
from ..models import StudyPlanEvent, StudyPlanMicroBadge

SLOTS = constants.MICROBADGES_PER_TOPIC


def target_dates(start_date, deadline, count=SLOTS):
    """``count`` dates spread evenly up to the Badge Test buffer before the deadline.

    The last lands ``BADGE_TEST_BUFFER_DAYS`` before the deadline, or on it for
    a run too short to leave that much room; none falls before the start.
    """
    last = deadline - timedelta(days=constants.BADGE_TEST_BUFFER_DAYS)
    if last <= start_date:
        last = deadline
    span = (last - start_date).days
    return [start_date + timedelta(days=round(span * n / count))
            for n in range(1, count + 1)]


def core_badges(goal):
    """The goal's ten core MicroBadges, in order. Uses a prefetch if there is one."""
    return sorted((b for b in goal.micro_badges.all() if b.kind == 'core'),
                  key=lambda b: b.number)


def retry_badges(goal):
    return sorted((b for b in goal.micro_badges.all() if b.kind == 'retry'),
                  key=lambda b: b.number)


def core_earned(goal):
    return sum(1 for b in core_badges(goal) if b.is_earned)


def all_core_earned(goal):
    badges = core_badges(goal)
    return bool(badges) and all(b.is_earned for b in badges)


def next_badge(goal):
    """The MicroBadge to lead with: a retry waiting, else the lowest core one left."""
    for badge in retry_badges(goal) + core_badges(goal):
        if not badge.is_earned:
            return badge
    return None


def is_complete(badge):
    """Every item still in it is done. An empty MicroBadge is never complete --
    it is waiting for a teacher to fill it or award it, not free."""
    items = badge.live_items()
    return bool(items) and all(i.status == 'done' for i in items)


def earn(badge, by_teacher=False, when=None):
    """Mark one MicroBadge earned and say so in the plan's log."""
    if badge.is_earned:
        return False
    badge.earned_at = when or timezone.now()
    badge.earned_by_teacher = by_teacher
    badge.save(update_fields=['earned_at', 'earned_by_teacher'])
    label = "Retry MicroBadge" if badge.is_retry else f"MicroBadge {badge.number}"
    StudyPlanEvent.log(
        badge.goal.plan, 'microbadge_earned',
        f"{badge.goal.topic.name}: {label} "
        f"{'awarded by the teacher' if by_teacher else 'earned'}")
    return True


def award(goals, when=None):
    """Earn every MicroBadge whose items are all done. Returns those earned."""
    earned = []
    for goal in goals:
        for badge in goal.micro_badges.prefetch_related('items'):
            if not badge.is_earned and is_complete(badge) and earn(badge, when=when):
                earned.append(badge)
    return earned


def goals_of(items):
    """The distinct goals behind some items, for awarding after they change."""
    seen = {}
    for item in items:
        if item.goal_id and item.goal_id not in seen:
            seen[item.goal_id] = item.goal
    return list(seen.values())


def add_retry_badge(goal, today=None):
    """A fresh MicroBadge after a failed Badge Test, numbered after the rest."""
    today = today or timezone.localdate()
    last = goal.micro_badges.order_by('-number').first()
    return StudyPlanMicroBadge.objects.create(
        goal=goal, kind='retry',
        number=(last.number + 1) if last else SLOTS + 1,
        target_date=today + timedelta(days=constants.RETRY_MICROBADGE_DAYS))


def overdue(goal, today=None):
    """Unearned MicroBadges further past their target than the teacher allows."""
    today = today or timezone.localdate()
    cutoff = today - timedelta(days=constants.BEHIND_FLAG_DAYS)
    return [b for b in goal.micro_badges.all()
            if not b.is_earned and b.target_date < cutoff]
