"""Choosing, unlocking and marking the checkpoints that decide mastery.

A checkpoint is two or three real exam parts. The student sits them, the marks
are added up, and passing the total *is* mastery for that topic. That is the
whole of it -- no weighted blend of attempt history, nothing a teacher cannot
recompute on paper from the marks shown.

Three rules here are less obvious than they look:

**The window.** Only attempts submitted at or after ``checkpoint.unlocked_at``
count. Without that, a checkpoint would be marked from work the student did
weeks before it was set.

**Penalties are applied here, not inherited.** The exam grader takes
``hint_used`` and ``solution_used`` arguments and docks marks for them, but
``exam_papers.views`` passes both as ``False`` (views.py:309), so the stored
``marks_awarded`` has no penalty in it. Applying the project's -20%/-50%
convention here is therefore a first deduction, not a second one.

**Taint is per part, not per attempt.** Viewing a marking scheme stamps
``solution_viewed`` on the student's *latest existing* attempt
(exam_papers/views.py:404), so the flag sits on the attempt *before* the one it
influenced. Any flagged attempt in the window therefore taints the whole part,
not just the attempt carrying the flag.
"""
import logging

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from exam_papers.models import ExamQuestionAttempt, ExamQuestionPart
from students.models import WorkSubmission

from .. import constants
from ..models import (
    StudyPlanCheckpoint, StudyPlanCheckpointPart, StudyPlanEvent, StudyPlanItem,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Choosing the parts
# ---------------------------------------------------------------------------

def reserved_part_ids(plan):
    """Parts already spoken for by any checkpoint in this plan.

    These must never be handed out as practice: a capstone sat on a question the
    student already worked through with the marking scheme open proves nothing.
    """
    return set(
        StudyPlanCheckpointPart.objects
        .filter(checkpoint__goal__plan=plan)
        .values_list('exam_question_part_id', flat=True)
    )


def practice_part_ids(plan):
    """Parts this plan has already issued as ordinary practice."""
    return set(
        StudyPlanItem.objects
        .filter(plan=plan, exam_question_part__isnull=False)
        .values_list('exam_question_part_id', flat=True)
    )


def attempted_part_ids(student, part_ids):
    """Of these parts, the ones the student has ever attempted."""
    if not part_ids:
        return set()
    return set(
        ExamQuestionAttempt.objects
        .filter(exam_attempt__student=student, question_part_id__in=part_ids)
        .values_list('question_part_id', flat=True)
    )


def candidate_parts(topic, plan=None, student=None):
    """Parts on this topic that could serve as a checkpoint, best first.

    Ranked so that the parts a student has never met, from the most recent
    papers, with their marks filled in, come first.
    """
    parts = list(
        ExamQuestionPart.objects
        .filter(topic=topic, question__exam_paper__is_published=True)
        .select_related('question__exam_paper', 'topic')
    )
    if not parts:
        return []

    blocked = set()
    if plan is not None:
        blocked = reserved_part_ids(plan) | practice_part_ids(plan)
    parts = [p for p in parts if p.id not in blocked]

    seen = attempted_part_ids(student, [p.id for p in parts]) if student else set()

    def rank(part):
        paper = part.question.exam_paper
        return (
            part.id in seen,                 # unseen first
            part.max_marks in (None, 0),     # marks filled in first
            -(paper.year or 0),              # most recent paper first
            part.question.question_number or 0,
            part.order or 0,
            part.id,
        )

    return sorted(parts, key=rank)


def spread_across_papers(parts, count):
    """Take `count` parts, avoiding two from one paper while that is possible."""
    chosen, used_papers, leftovers = [], set(), []
    for part in parts:
        if len(chosen) == count:
            break
        paper_id = part.question.exam_paper_id
        if paper_id in used_papers:
            leftovers.append(part)
            continue
        chosen.append(part)
        used_papers.add(paper_id)
    for part in leftovers:
        if len(chosen) == count:
            break
        chosen.append(part)
    return chosen


def suggest_parts(goal, count=None):
    """The shortlist a teacher picks a checkpoint from."""
    count = count or goal.checkpoint_size
    pool = candidate_parts(goal.topic, plan=goal.plan, student=goal.plan.student)
    return spread_across_papers(pool, count)


def pool_report(goal):
    """How much unseen material this topic has, for the builder's warnings.

    A topic needs enough parts for the first checkpoint *and* its retries, or a
    student who fails twice meets a question they have already worked through.
    """
    needed = goal.checkpoint_size * (1 + constants.RETRY_ROUNDS)
    available = len(candidate_parts(goal.topic, plan=goal.plan,
                                    student=goal.plan.student))
    return {
        'topic': goal.topic,
        'available': available,
        'needed': needed,
        'sufficient': available >= needed,
        'can_start': available >= goal.checkpoint_size,
    }


# ---------------------------------------------------------------------------
# Building one
# ---------------------------------------------------------------------------

@transaction.atomic
def create_checkpoint(goal, parts=None, round_number=None, status='locked'):
    """Set a checkpoint for this goal from the given parts.

    ``pass_mark`` is copied off the goal now rather than read through the
    relation later, so that changing the target next term cannot turn a pass
    already earned into a fail.
    """
    if round_number is None:
        last = goal.checkpoints.order_by('-round').first()
        round_number = (last.round + 1) if last else 1

    if parts is None:
        parts = suggest_parts(goal)
    parts = list(parts)
    if not parts:
        return None

    checkpoint = StudyPlanCheckpoint.objects.create(
        goal=goal,
        round=round_number,
        status=status,
        pass_mark=goal.target_mastery,
        unlocked_at=timezone.now() if status == 'ready' else None,
    )
    for order, part in enumerate(parts, start=1):
        StudyPlanCheckpointPart.objects.create(
            checkpoint=checkpoint,
            exam_question_part=part,
            order=order,
            # Snapshot: filling in a part's max_marks later must not change what
            # this checkpoint was worth when it was sat.
            marks_possible=part.max_marks or _fallback_marks(part),
        )
    return checkpoint


def _fallback_marks(part):
    """A defensible mark for a part whose max_marks was never filled in."""
    siblings = [p.max_marks for p in part.question.parts.all() if p.max_marks]
    if siblings:
        return round(sum(siblings) / len(siblings))
    total = part.question.total_marks
    count = part.question.parts.count() or 1
    if total:
        return max(1, round(total / count))
    return 10


def unlock(checkpoint, when=None):
    """Open a checkpoint for sitting. Only work from now on counts."""
    if checkpoint.status != 'locked':
        return checkpoint
    checkpoint.status = 'ready'
    checkpoint.unlocked_at = when or timezone.now()
    checkpoint.save(update_fields=['status', 'unlocked_at'])
    StudyPlanEvent.log(
        checkpoint.goal.plan, 'checkpoint_unlocked',
        f"{checkpoint.goal.topic.name}: Badge Test {checkpoint.round} ready to sit",
        checkpoint=checkpoint)
    return checkpoint


# ---------------------------------------------------------------------------
# Marking it
# ---------------------------------------------------------------------------

def _penalty_factor(hint_used, solution_viewed):
    """The project's help deductions: -20% for a hint, -50% for a solution.

    Multiplicative where both apply, matching
    exam_papers/services/vision_grading.py:437-442.
    """
    factor = 1.0
    if hint_used:
        factor *= (1 - constants.HINT_PENALTY)
    if solution_viewed:
        factor *= (1 - constants.SOLUTION_PENALTY)
    return factor


def attempts_in_window(checkpoint):
    """{part_id: [attempts]} for work done since the checkpoint opened."""
    part_ids = [p.exam_question_part_id for p in checkpoint.parts.all()]
    if not part_ids or checkpoint.unlocked_at is None:
        return {}
    rows = (ExamQuestionAttempt.objects
            .filter(exam_attempt__student=checkpoint.goal.plan.student,
                    question_part_id__in=part_ids,
                    submitted_at__gte=checkpoint.unlocked_at)
            .order_by('question_part_id', '-marks_awarded'))
    by_part = {}
    for row in rows:
        by_part.setdefault(row.question_part_id, []).append(row)
    return by_part


def photos_in_window(checkpoint):
    """{part_id: [work photos]} that gave a mark since the checkpoint opened.

    Empty unless WORK_PHOTO_COUNTS_ON_CHECKPOINTS is on. Only a photo the
    analysis was willing to put a mark on counts: work_analysis withholds one
    for an unreadable page, low confidence or no working, and that decision is
    not second-guessed here.
    """
    if not getattr(settings, 'WORK_PHOTO_COUNTS_ON_CHECKPOINTS', False):
        return {}
    part_ids = [p.exam_question_part_id for p in checkpoint.parts.all()]
    if not part_ids or checkpoint.unlocked_at is None:
        return {}
    rows = (WorkSubmission.objects
            .filter(student__user=checkpoint.goal.plan.student,
                    exam_question_part_id__in=part_ids,
                    status=WorkSubmission.Status.COMPLETE,
                    estimated_mark__isnull=False,
                    estimated_max_marks__gt=0,
                    created_at__gte=checkpoint.unlocked_at)
            .order_by('exam_question_part_id', '-created_at'))
    by_part = {}
    for row in rows:
        by_part.setdefault(row.exam_question_part_id, []).append(row)
    return by_part


def answered_part_ids(checkpoint):
    """Parts with a typed answer, or a marked photo, since it opened."""
    return set(attempts_in_window(checkpoint)) | set(photos_in_window(checkpoint))


def is_sat(checkpoint):
    """True once every part has been answered since the checkpoint opened."""
    answered = answered_part_ids(checkpoint)
    return all(p.exam_question_part_id in answered for p in checkpoint.parts.all())


@transaction.atomic
def grade(checkpoint, when=None):
    """Mark a sat checkpoint and freeze the result onto it.

    Returns the checkpoint. Already-decided checkpoints are returned untouched,
    which is what makes the nightly run safe to repeat.
    """
    if checkpoint.is_decided:
        return checkpoint

    by_part = attempts_in_window(checkpoint)
    photos = photos_in_window(checkpoint)
    parts = list(checkpoint.parts.select_related('exam_question_part'))
    if not all(p.exam_question_part_id in by_part or p.exam_question_part_id in photos
               for p in parts):
        return checkpoint  # not sat yet

    total_awarded = 0.0
    total_possible = 0.0
    any_solution = False

    for part in parts:
        attempts = by_part.get(part.exam_question_part_id, [])

        # Taint is per part: the flag lands on the attempt before the one it
        # influenced, so any flagged attempt taints the lot -- a photo's mark
        # included, since a scheme opened is opened whichever way you answer.
        hint_used = any(a.hint_used for a in attempts)
        solution_viewed = any(a.solution_viewed for a in attempts)
        any_solution = any_solution or solution_viewed

        # The better of the best typed answer and the best photo.
        ratio, when, from_photo = 0.0, None, False
        if attempts:
            best = attempts[0]  # ordered by -marks_awarded
            max_marks = best.max_marks or part.marks_possible or 1
            ratio = (best.marks_awarded or 0) / max_marks
            when = best.submitted_at
        for photo in photos.get(part.exam_question_part_id, []):
            photo_ratio = photo.estimated_mark / photo.estimated_max_marks
            if when is None or photo_ratio > ratio:
                ratio, when, from_photo = photo_ratio, photo.created_at, True
        ratio = max(0.0, min(1.0, ratio)) * _penalty_factor(hint_used, solution_viewed)

        part.marks_awarded = round(ratio * part.marks_possible, 2)
        part.score = round(ratio * 100, 1)
        part.attempted_at = when
        part.hint_used = hint_used
        part.solution_viewed = solution_viewed
        part.marked_from_photo = from_photo
        part.save(update_fields=['marks_awarded', 'score', 'attempted_at',
                                 'hint_used', 'solution_viewed',
                                 'marked_from_photo'])

        total_awarded += part.marks_awarded
        total_possible += part.marks_possible

    score = (100 * total_awarded / total_possible) if total_possible else 0.0
    checkpoint.marks_awarded = round(total_awarded, 2)
    checkpoint.marks_possible = round(total_possible, 2)
    checkpoint.score = round(score, 1)
    checkpoint.is_clean = not any_solution
    checkpoint.sat_at = when or timezone.now()
    checkpoint.status = 'passed' if score >= checkpoint.pass_mark else 'failed'
    checkpoint.save(update_fields=['marks_awarded', 'marks_possible', 'score',
                                   'is_clean', 'sat_at', 'status'])
    return checkpoint


@transaction.atomic
def record_result(checkpoint):
    """Write a decided checkpoint through to its goal.

    A pass is copied onto the goal so the progress card and the achievements
    page stay single cheap queries.
    """
    goal = checkpoint.goal
    plan = goal.plan

    if checkpoint.status == 'passed':
        goal.mastered_at = checkpoint.sat_at
        goal.mastery_score = checkpoint.score
        goal.save(update_fields=['mastered_at', 'mastery_score'])
        StudyPlanEvent.log(
            plan, 'checkpoint_passed',
            f"{goal.topic.name}: passed Badge Test {checkpoint.round} "
            f"with {checkpoint.score:.0f}%"
            + ("" if checkpoint.is_clean else " (marking scheme was opened)"),
            checkpoint=checkpoint)
        StudyPlanEvent.log(
            plan, 'goal_mastered',
            f"{goal.topic.name} mastered at {checkpoint.score:.0f}%",
            checkpoint=checkpoint)
        # Unsat future rounds are no longer needed; void rather than delete so
        # the record of what was reserved survives.
        goal.checkpoints.filter(status='locked').update(status='voided')
        return 'passed'

    if checkpoint.status == 'failed':
        StudyPlanEvent.log(
            plan, 'checkpoint_failed',
            f"{goal.topic.name}: Badge Test {checkpoint.round} scored "
            f"{checkpoint.score:.0f}%, needed {checkpoint.pass_mark}%",
            checkpoint=checkpoint)
        return 'failed'

    return checkpoint.status


def next_round(goal, open_now=True):
    """Set up the next Badge Test after a fail, or tell the teacher we are out.

    ``open_now=False`` leaves it locked behind the retry MicroBadge the fail
    added; the nightly run opens it once that is earned.

    Never reuses a part the student has already met -- if the reserved pool is
    exhausted, the goal is flagged instead, because a test on a seen question
    is not evidence of anything.
    """
    pending = goal.checkpoints.filter(status='locked').order_by('round').first()
    if pending:
        return unlock(pending) if open_now else pending

    parts = suggest_parts(goal)
    if len(parts) < 1:
        goal.flag("No unseen exam parts left for another Badge Test")
        StudyPlanEvent.log(
            goal.plan, 'attention',
            f"{goal.topic.name}: ran out of unseen exam parts for a new Badge Test")
        return None

    return create_checkpoint(goal, parts=parts,
                             status='ready' if open_now else 'locked')
