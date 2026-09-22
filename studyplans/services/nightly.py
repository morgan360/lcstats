"""The work the plan does for itself: marking, unlocking, and adding more.

Every function here is safe to run twice. That is not a nicety -- it is what
lets the nightly cron, the teacher's "run now" button and the student's refresh
all call the same code without racing each other into a mess.

The hard rule is that nothing is ever deleted and nothing a teacher chose is
ever moved. An item is retired by setting its status to ``skipped``; a
checkpoint no longer needed becomes ``voided``. A plan that quietly throws away
a teacher's work is one they will stop using after the first time it surprises
them, so every automated change also writes a StudyPlanEvent saying what it did.
"""
import logging

from django.db import transaction
from django.utils import timezone

from .. import constants
from ..models import StudyPlanEvent, StudyPlanItem
from . import checkpoints as checkpoint_service
from . import completion, estimates, microbadges, planner

logger = logging.getLogger(__name__)


def _plan_items(plan):
    return (plan.items
            .exclude(status__in=('done', 'skipped'))
            .select_related('section', 'exam_question', 'exam_question_part',
                            'quickkick', 'flashcard_set', 'micro_badge', 'goal'))


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------

def detect_completions(plan, today=None, dry_run=False):
    """Mark items whose evidence says they are done."""
    today = today or timezone.localdate()
    items = [i for i in _plan_items(plan) if i.available_from <= today]
    if dry_run:
        outcomes = completion.evaluate(items, student=plan.student)
        return [i for i in items
                if outcomes.get(i.id) and outcomes[i.id].status != i.status]
    return completion.persist(items, student=plan.student)


def award_microbadges(plan, dry_run=False):
    """Earn every MicroBadge whose work is all done."""
    goals = list(plan.goals.all())
    if dry_run:
        return [b for goal in goals
                for b in goal.micro_badges.prefetch_related('items')
                if not b.is_earned and microbadges.is_complete(b)]
    return microbadges.award(goals)


def unlock_due_checkpoints(plan, dry_run=False):
    """Open the Badge Test of any goal that has earned its way to it.

    Round one opens when all ten core MicroBadges are earned. A later round,
    after a fail, opens when the retry MicroBadge the fail added is earned --
    or at once if there was no fresh practice left to put in one.
    """
    unlocked = []
    for goal in plan.goals.prefetch_related('micro_badges', 'checkpoints'):
        if goal.mastered_at:
            continue
        checkpoint = goal.checkpoints.filter(status='locked').order_by('round').first()
        if checkpoint is None:
            continue
        if checkpoint.round == 1:
            if not microbadges.all_core_earned(goal):
                continue
        else:
            if not goal.checkpoints.filter(status='failed').exists():
                continue
            retries = microbadges.retry_badges(goal)
            if retries and not retries[-1].is_earned:
                continue
        if not dry_run:
            checkpoint_service.unlock(checkpoint)
        unlocked.append(checkpoint)
    return unlocked


def grade_sat_checkpoints(plan, dry_run=False):
    """Mark any checkpoint the student has finished sitting."""
    graded = []
    for goal in plan.goals.prefetch_related('checkpoints__parts'):
        for checkpoint in goal.checkpoints.filter(status='ready'):
            if not checkpoint_service.is_sat(checkpoint):
                continue
            if dry_run:
                graded.append(checkpoint)
                continue
            checkpoint_service.grade(checkpoint)
            if checkpoint.is_decided:
                outcome = checkpoint_service.record_result(checkpoint)
                if outcome == 'passed':
                    _retire_goal_work(plan, goal)
                elif outcome == 'failed':
                    _after_failure(plan, goal)
                graded.append(checkpoint)
    return graded


def _retire_goal_work(plan, goal):
    """A mastered topic should stop asking for more practice."""
    remaining = [i for i in goal.items.filter(status__in=('pending', 'attempted'))
                 if not i.is_locked_for_automation]
    for item in remaining:
        item.status = 'skipped'
        item.save(update_fields=['status', 'updated_at'])
    if remaining:
        StudyPlanEvent.log(
            plan, 'teacher_edit',
            f"{goal.topic.name} mastered -- {len(remaining)} remaining "
            f"task(s) no longer needed")


def _after_failure(plan, goal, today=None):
    """A retry MicroBadge of fresh practice, then the next Badge Test.

    The next round waits for the retry MicroBadge, so a student practises what
    went wrong before trying again. With no fresh practice left to offer, the
    next round opens at once rather than behind an empty MicroBadge.
    """
    candidates = revisit_candidates(plan, goal)[:constants.MAX_REVISITS_PER_RETRY]
    if not candidates:
        checkpoint_service.next_round(goal)
        return
    badge = microbadges.add_retry_badge(goal, today)
    injected = inject_revisits(plan, goal, badge, candidates)
    checkpoint = checkpoint_service.next_round(goal, open_now=False)
    if checkpoint:
        StudyPlanEvent.log(
            plan, 'injected',
            f"{goal.topic.name}: added a retry MicroBadge of {injected} task(s); "
            f"Badge Test {checkpoint.round} opens once it is earned")


def issued(plan, count_removed=True):
    """(kind, id) of every piece of content this plan has handed out.

    ``count_removed=False`` leaves out what a teacher removed, so it can be
    offered back to them. The automatic side never passes that: work a teacher
    took off the plan must not reappear overnight.
    """
    refs = set()
    for item in plan.items.all():
        if not count_removed and item.status == 'skipped':
            continue
        obj_id = {'section': item.section_id,
                  'exam_part': item.exam_question_part_id,
                  'exam_question': item.exam_question_id,
                  'quickkick': item.quickkick_id,
                  'flashcard': item.flashcard_set_id}.get(item.content_type)
        if obj_id:
            refs.add((item.content_type, obj_id))
    return refs


def revisit_candidates(plan, goal, allow_removed=False):
    """Practice on this topic the plan has not handed out, best first.

    ``allow_removed=True`` also offers back anything the teacher removed --
    for the teacher's own Add list, where undoing a mistaken removal is the
    point. Parts held back for a Badge Test are never offered either way.
    """
    excluded = (checkpoint_service.reserved_part_ids(plan)
                | checkpoint_service.practice_part_ids(
                    plan, count_removed=not allow_removed))
    already = issued(plan, count_removed=not allow_removed)
    return [c for c in planner.candidates_for_goal(plan.student, goal.topic, excluded)
            if (c.kind, c.obj.id) not in already]


def inject_revisits(plan, goal, badge, candidates, today=None):
    """Put a little more practice on a topic that did not pass into ``badge``.

    Never more than a couple of items, so a struggling student is not buried.
    """
    today = today or timezone.localdate()
    added = 0
    for order, candidate in enumerate(candidates, start=1):
        item = StudyPlanItem(
            plan=plan, goal=goal, micro_badge=badge, content_type=candidate.kind,
            estimated_minutes=candidate.minutes, order=order, origin='revisit',
            available_from=today, due_date=max(today, badge.target_date))
        field = {'section': 'section', 'exam_part': 'exam_question_part',
                 'exam_question': 'exam_question', 'quickkick': 'quickkick',
                 'flashcard': 'flashcard_set'}.get(candidate.kind)
        if field:
            setattr(item, field, candidate.obj)
        item.save()
        added += 1
    return added


def flag_if_behind(plan, today=None, dry_run=False):
    """Tell the teacher about a topic whose MicroBadges have stalled.

    Nothing is moved: a MicroBadge's target date is a pace, and a student who
    is behind needs a conversation, not their work reshuffled. A goal already
    flagged is not flagged again.
    """
    flagged = []
    for goal in plan.goals.prefetch_related('micro_badges'):
        if goal.mastered_at or goal.needs_teacher_attention:
            continue
        late = microbadges.overdue(goal, today)
        if not late:
            continue
        first = late[0]
        label = ("the retry MicroBadge" if first.is_retry
                 else f"MicroBadge {first.number}")
        if not dry_run:
            goal.flag(f"{label} is well past its target of "
                      f"{first.target_date:%-d %b}")
            StudyPlanEvent.log(
                plan, 'attention',
                f"{goal.topic.name}: {label} is more than "
                f"{constants.BEHIND_FLAG_DAYS} days past its target")
        flagged.append(goal)
    return flagged


def close_if_finished(plan, today=None, dry_run=False):
    """Mark a plan completed once every goal is mastered."""
    today = today or timezone.localdate()
    goals = list(plan.goals.all())
    if not goals or plan.status != 'active':
        return False
    if not all(g.mastered_at for g in goals):
        return False
    if not dry_run:
        plan.status = 'completed'
        plan.save(update_fields=['status'])
        StudyPlanEvent.log(plan, 'goal_mastered', "Every topic mastered")
    return True


# ---------------------------------------------------------------------------
# The whole run
# ---------------------------------------------------------------------------

def run_for_plan(plan, today=None, dry_run=False):
    """Everything the plan does for itself, in order. Safe to repeat."""
    today = today or timezone.localdate()
    summary = {'plan': plan, 'completed': 0, 'earned': 0, 'unlocked': 0,
               'graded': 0, 'behind': 0, 'closed': False}

    if plan.is_locked or plan.status != 'active':
        return summary

    with transaction.atomic():
        summary['completed'] = len(detect_completions(plan, today, dry_run))
        summary['earned'] = len(award_microbadges(plan, dry_run))
        summary['unlocked'] = len(unlock_due_checkpoints(plan, dry_run))
        summary['graded'] = len(grade_sat_checkpoints(plan, dry_run))
        summary['behind'] = len(flag_if_behind(plan, today, dry_run))
        summary['closed'] = close_if_finished(plan, today, dry_run)

        if not dry_run:
            plan.last_checked_at = timezone.now()
            plan.save(update_fields=['last_checked_at'])

    return summary


def active_plans(student=None, plan_id=None):
    from ..models import StudyPlan
    plans = StudyPlan.objects.filter(status='active', is_locked=False)
    if plan_id:
        plans = plans.filter(id=plan_id)
    if student:
        plans = plans.filter(student=student)
    return plans.select_related('student', 'subject', 'teacher')

