"""Deciding when a piece of planned work counts as done.

Two things separate this from ``homework.StudentHomeworkProgress.check_auto_completion``,
and both are deliberate.

**There is a window.** Only work done on or after ``item.available_from`` counts.
Homework's version has none, so an assignment set today is satisfied by attempts
made in September. A study plan set for Christmas that marks itself complete the
moment it is created is worse than no plan at all.

**Existence is not evidence.** Homework completes a task as soon as any attempt
row exists. But opening a flashcard set creates an attempt row for every card in
it (flashcards/views.py:103), and opening a QuickFlick creates a view row
(quickkicks/views.py:56). Those rows mean a page was loaded, nothing more. So
flashcards are measured against every card in the published set, a QuickFlick
with a question needs the question answered, and a section needs most of its
questions attempted at a passing standard.

Nothing here writes during a GET. ``evaluate`` reads; ``persist`` writes, and is
called from the nightly command and from an explicit POST.
"""
import logging
import math
from datetime import datetime, time

from django.utils import timezone

from exam_papers.models import ExamQuestionAttempt
from flashcards.models import Flashcard, FlashcardAttempt
from quickkicks.models import QuickKickView
from students.models import QuestionAttempt

from .. import constants

logger = logging.getLogger(__name__)


def window_start(item):
    """An aware datetime at midnight on the day this item became available."""
    return timezone.make_aware(datetime.combine(item.available_from, time.min))


class Outcome:
    """What the evidence says about one item."""

    __slots__ = ('status', 'score', 'note')

    def __init__(self, status='pending', score=None, note=''):
        self.status = status
        self.score = score
        self.note = note

    def __repr__(self):
        return f"<Outcome {self.status} {self.score} {self.note!r}>"


# ---------------------------------------------------------------------------
# One rule per kind
# ---------------------------------------------------------------------------

def _exam_part_outcome(student, part, since):
    rows = list(ExamQuestionAttempt.objects
                .filter(exam_attempt__student=student, question_part=part,
                        submitted_at__gte=since)
                .values_list('marks_awarded', 'max_marks', 'submitted_at'))
    if not rows:
        return Outcome()

    best_ratio, best_marks, best_max, best_when = 0.0, 0, 0, None
    for awarded, max_marks, when in rows:
        if not max_marks:
            continue
        ratio = max(0.0, min(1.0, (awarded or 0) / max_marks))
        if ratio >= best_ratio:
            best_ratio, best_marks, best_max, best_when = (
                ratio, awarded or 0, max_marks, when)

    if best_when is None:
        # Attempts exist but none recorded a mark out of anything.
        return Outcome('attempted', None, "Attempted")

    note = (f"Best {best_marks:g}/{best_max} on "
            f"{timezone.localtime(best_when):%-d %b}")
    score = round(best_ratio * 100, 1)
    if best_ratio >= constants.EXAM_PART_DONE_RATIO:
        return Outcome('done', score, note)
    return Outcome('attempted', score, f"Best so far {best_marks:g}/{best_max}")


def _exam_question_outcome(student, question, since):
    parts = list(question.parts.all())
    if not parts:
        return Outcome()
    done = 0
    attempted = 0
    for part in parts:
        outcome = _exam_part_outcome(student, part, since)
        if outcome.status == 'done':
            done += 1
            attempted += 1
        elif outcome.status == 'attempted':
            attempted += 1
    if not attempted:
        return Outcome()
    ratio = done / len(parts)
    if ratio >= constants.EXAM_QUESTION_DONE_RATIO:
        return Outcome('done', round(ratio * 100, 1),
                       f"{done} of {len(parts)} parts done")
    return Outcome('attempted', round(ratio * 100, 1),
                   f"{done} of {len(parts)} parts done")


def _section_outcome(student, section, since):
    total = section.questions.count()
    if not total:
        return Outcome()
    rows = list(QuestionAttempt.objects
                .filter(student__user=student, question__section=section,
                        attempted_at__gte=since)
                .values_list('question_id', 'score_awarded'))
    if not rows:
        return Outcome()

    best = {}
    for question_id, score in rows:
        if score is None:
            score = 0
        if score > best.get(question_id, -1):
            best[question_id] = score

    attempted = len(best)
    mean = sum(best.values()) / attempted
    needed = math.ceil(constants.SECTION_DONE_RATIO * total)
    note = f"{attempted} of {total} questions, averaging {mean:.0f}%"

    if attempted >= needed and mean >= constants.SECTION_DONE_MEAN_SCORE:
        return Outcome('done', round(mean, 1), note)
    return Outcome('attempted', round(mean, 1), note)


def _flashcard_outcome(student, flashcard_set, since):
    total = Flashcard.objects.filter(flashcard_set=flashcard_set).count()
    if not total:
        return Outcome()

    attempts = list(FlashcardAttempt.objects
                    .filter(student=student, flashcard__flashcard_set=flashcard_set)
                    .values_list('mastery_level', 'last_answered_at'))
    # Opening a set creates a row per card, so an unanswered row is not evidence.
    answered_in_window = any(
        when is not None and when >= since for _level, when in attempts)
    if not answered_in_window:
        return Outcome()

    mastered = sum(1 for level, _when in attempts
                   if level in ('know', 'retired'))
    ratio = mastered / total
    note = f"{mastered} of {total} cards known"
    if ratio >= constants.FLASHCARD_DONE_RATIO:
        return Outcome('done', round(ratio * 100, 1), note)
    return Outcome('attempted', round(ratio * 100, 1), note)


def _quickkick_outcome(student, quickkick, since):
    view = (QuickKickView.objects
            .filter(user=student, quickkick=quickkick)
            .first())
    if view is None:
        return Outcome()

    seen_in_window = view.viewed_at is not None and view.viewed_at >= since
    answered_in_window = (view.last_attempt_at is not None
                          and view.last_attempt_at >= since)

    if not quickkick.question_id:
        # Nothing to answer, so watching it is the whole task.
        if seen_in_window:
            return Outcome('done', None, "Watched")
        return Outcome()

    if not answered_in_window:
        return Outcome('attempted' if seen_in_window else 'pending', None,
                       "Watched, question not answered yet" if seen_in_window else "")

    score = float(view.score_awarded or 0)
    if view.answer_correct or score >= constants.QUICKKICK_DONE_SCORE:
        return Outcome('done', score, "Question answered")
    return Outcome('attempted', score, "Question answered, not yet right")


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def outcome_for(item, student=None):
    """What the evidence says about one item. Reads only."""
    student = student or item.plan.student
    since = window_start(item)
    kind = item.content_type

    if kind == 'exam_part' and item.exam_question_part:
        return _exam_part_outcome(student, item.exam_question_part, since)
    if kind == 'exam_question' and item.exam_question:
        return _exam_question_outcome(student, item.exam_question, since)
    if kind == 'section' and item.section:
        return _section_outcome(student, item.section, since)
    if kind == 'flashcard' and item.flashcard_set:
        return _flashcard_outcome(student, item.flashcard_set, since)
    if kind == 'quickkick' and item.quickkick:
        return _quickkick_outcome(student, item.quickkick, since)

    # A written exercise has nothing to measure; the student ticks it.
    return Outcome()


def evaluate(items, student=None):
    """{item_id: Outcome} for items worth checking. Reads only."""
    results = {}
    for item in items:
        if item.status in ('done', 'skipped'):
            continue
        results[item.id] = outcome_for(item, student)
    return results


def persist(items, student=None, when=None):
    """Apply outcomes to items. Returns the ones that changed.

    Only ever moves an item forward -- pending to attempted to done -- so
    running it twice is a no-op and a student cannot lose a tick by revisiting
    work and doing worse.
    """
    changed = []
    now = when or timezone.now()
    for item in items:
        if item.status in ('done', 'skipped'):
            continue
        outcome = outcome_for(item, student)
        if outcome.status == 'done':
            item.status = 'done'
            item.completed_at = now
            item.evidence_score = outcome.score
            item.evidence_note = outcome.note[:200]
            item.save(update_fields=['status', 'completed_at', 'evidence_score',
                                     'evidence_note', 'updated_at'])
            changed.append(item)
        elif outcome.status == 'attempted' and item.status == 'pending':
            item.status = 'attempted'
            item.evidence_score = outcome.score
            item.evidence_note = outcome.note[:200]
            if item.started_at is None:
                item.started_at = now
            item.save(update_fields=['status', 'started_at', 'evidence_score',
                                     'evidence_note', 'updated_at'])
            changed.append(item)
    return changed
