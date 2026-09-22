"""Stamp cards: one per topic, drawn from the student's study plans.

A card shows a topic's ten MicroBadges and its full badge. Both come from plans
-- current, finished or archived -- and nowhere else: a MicroBadge is a bundle
of plan work, and the full badge is a passed Badge Test, which only opens once
all ten are earned. A topic the student has never had on a plan shows blank.

Where a student has had a topic on more than one plan, the card shows the best
of them: a passed Badge Test first, otherwise the most MicroBadges earned.
MicroBadges are never un-earned, so a card never goes backwards.

Reads only.
"""
from interactive_lessons.models import Topic

from .. import constants
from ..models import StudyPlanGoal
from . import microbadges

SLOTS = constants.MICROBADGES_PER_TOPIC


def _latest(*moments):
    moments = [m for m in moments if m is not None]
    return max(moments) if moments else None


def _card(topic, goals):
    """One topic's card from every goal the student has had on it."""
    best_earned, first_pass, active, last_activity = 0, None, False, None
    for goal in goals:
        best_earned = max(best_earned, microbadges.core_earned(goal))
        active = active or goal.plan.status == 'active'
        for badge in goal.micro_badges.all():
            last_activity = _latest(last_activity, badge.earned_at)
        for checkpoint in goal.checkpoints.all():
            if checkpoint.status != 'passed':
                continue
            last_activity = _latest(last_activity, checkpoint.sat_at)
            if first_pass is None or (checkpoint.sat_at and first_pass.sat_at
                                      and checkpoint.sat_at < first_pass.sat_at):
                first_pass = checkpoint
    return {
        'topic': topic,
        'microstamps': best_earned,
        'micro': [n < best_earned for n in range(SLOTS)],
        'slots': SLOTS,
        'on_plan': bool(goals),
        'active': active,
        'stamped': first_pass is not None,
        'stamped_at': first_pass.sat_at if first_pass else None,
        'score': first_pass.score if first_pass else None,
        'last_activity': last_activity,
    }


def cards_for(user, subject=None, topics=None):
    """A card for every topic, in topic order; blank where never on a plan.

    ``topics`` narrows the set; otherwise it is every topic in ``subject``, or
    in every subject if that is None too. Drafts are left out -- a student
    cannot see a draft plan, so it must not fill their card either.
    """
    if topics is None:
        topics = Topic.objects.all()
        if subject is not None:
            topics = topics.filter(subject=subject)
    topics = list(topics)

    goals = (StudyPlanGoal.objects
             .filter(plan__student=user, topic__in=topics)
             .exclude(plan__status='draft')
             .select_related('plan')
             .prefetch_related('micro_badges', 'checkpoints'))
    by_topic = {}
    for goal in goals:
        by_topic.setdefault(goal.topic_id, []).append(goal)

    return [_card(topic, by_topic.get(topic.id, [])) for topic in topics]


def recent_cards(user, subject=None, limit=4):
    """Cards for topics on a plan: the active plan's first, then most recent."""
    cards = [c for c in cards_for(user, subject) if c['on_plan']]
    cards.sort(key=lambda c: (c['active'],
                              c['last_activity'].timestamp()
                              if c['last_activity'] else 0), reverse=True)
    return cards[:limit]
