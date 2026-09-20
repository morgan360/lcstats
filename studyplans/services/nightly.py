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
from . import completion, estimates, planner

logger = logging.getLogger(__name__)


def _plan_items(plan):
    return (plan.items
            .exclude(status__in=('done', 'skipped'))
            .select_related('section', 'exam_question', 'exam_question_part',
                            'quickkick', 'flashcard_set', 'week', 'goal'))


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


def unlock_due_checkpoints(plan, dry_run=False):
    """Open the checkpoint of any goal whose practice is mostly finished."""
    unlocked = []
    for goal in plan.goals.prefetch_related('items', 'checkpoints'):
        if goal.mastered_at:
            continue
        checkpoint = goal.checkpoints.filter(status='locked').order_by('round').first()
        if checkpoint is None:
            continue
        # Only round one unlocks on progress; later rounds are opened by a fail.
        if checkpoint.round > 1 and not goal.checkpoints.filter(
                status='failed').exists():
            continue
        if checkpoint_service.unlock_ratio(goal) < constants.CHECKPOINT_UNLOCK_RATIO:
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


def _after_failure(plan, goal):
    """More work on what went wrong, then a fresh checkpoint."""
    injected = inject_revisits(plan, goal)
    checkpoint = checkpoint_service.next_round(goal)
    if checkpoint and injected:
        StudyPlanEvent.log(
            plan, 'injected',
            f"{goal.topic.name}: added {injected} task(s) and set "
            f"checkpoint {checkpoint.round}")


def inject_revisits(plan, goal, today=None):
    """Add a little more practice on a topic that did not pass.

    Draws only on material this plan has not already issued, and never more than
    a couple of items, so a struggling student is not buried.
    """
    today = today or timezone.localdate()
    week = plan.current_week(today)
    if week is None:
        return 0

    excluded = (checkpoint_service.reserved_part_ids(plan)
                | checkpoint_service.practice_part_ids(plan))
    issued_sections = set(plan.items.filter(section__isnull=False)
                          .values_list('section_id', flat=True))

    candidates = planner.candidates_for_goal(plan.student, goal.topic, excluded)
    candidates = [c for c in candidates
                  if not (c.kind == 'section' and c.obj.id in issued_sections)]

    added = 0
    next_order = (week.items.count() or 0) + 1
    for candidate in candidates[:constants.MAX_REVISITS_PER_TOPIC_PER_WEEK]:
        item = StudyPlanItem(
            plan=plan, week=week, goal=goal, content_type=candidate.kind,
            estimated_minutes=candidate.minutes, order=next_order,
            origin='revisit',
            available_from=max(today, week.start_date),
            due_date=week.end_date)
        field = {'section': 'section', 'exam_part': 'exam_question_part',
                 'exam_question': 'exam_question', 'quickkick': 'quickkick',
                 'flashcard': 'flashcard_set'}.get(candidate.kind)
        if field:
            setattr(item, field, candidate.obj)
        item.save()
        next_order += 1
        added += 1
    return added


def carry_forward(plan, today=None, dry_run=False):
    """Move overdue work into the current week, up to a point.

    After a few carries the plan stops shuffling it along and tells the teacher
    instead: work that has been rolled forward three weeks running is not a
    scheduling problem.
    """
    today = today or timezone.localdate()
    week = plan.current_week(today)
    if week is None:
        return []

    overdue = [i for i in _plan_items(plan)
               if i.due_date < today and i.week_id != week.id
               and not i.is_locked_for_automation]

    carried = []
    for item in overdue:
        if item.carried_over_count >= constants.MAX_CARRY_OVERS:
            if not item.needs_teacher_attention and not dry_run:
                item.needs_teacher_attention = True
                item.save(update_fields=['needs_teacher_attention', 'updated_at'])
                StudyPlanEvent.log(
                    plan, 'attention',
                    f"Still not done after {item.carried_over_count} weeks: "
                    f"{item.get_content_display()}", item=item)
            continue
        if not dry_run:
            item.week = week
            item.available_from = max(item.available_from, week.start_date)
            item.due_date = week.end_date
            item.carried_over_count += 1
            item.save(update_fields=['week', 'available_from', 'due_date',
                                     'carried_over_count', 'updated_at'])
        carried.append(item)

    if carried and not dry_run:
        StudyPlanEvent.log(
            plan, 'carried',
            f"Moved {len(carried)} unfinished task(s) into week {week.index}")
    return carried


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
    summary = {'plan': plan, 'completed': 0, 'unlocked': 0, 'graded': 0,
               'carried': 0, 'closed': False}

    if plan.is_locked or plan.status != 'active':
        return summary

    with transaction.atomic():
        summary['completed'] = len(detect_completions(plan, today, dry_run))
        summary['unlocked'] = len(unlock_due_checkpoints(plan, dry_run))
        summary['graded'] = len(grade_sat_checkpoints(plan, dry_run))
        summary['carried'] = len(carry_forward(plan, today, dry_run))
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
