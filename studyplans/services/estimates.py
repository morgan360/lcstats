"""How long a piece of work should take.

Nothing in the database records difficulty or duration, so everything here is
inferred. The one established convention in the project is half a minute per
mark -- ``ExamQuestion.suggested_time_seconds`` is ``total_marks * 30``
(exam_papers/models.py:160) -- and the rest is built to agree with it.

These numbers decide how much a week holds, so they are stored on the item once
it is created rather than recomputed. A teacher filling in a part's ``max_marks``
next month must not silently rewrite the budget of a week already worked.
"""
import math

SECONDS_PER_MARK = 30

DEFAULT_EXAM_PART_MARKS = 10
DEFAULT_EXAM_QUESTION_MINUTES = 15
MINUTES_PER_SECTION_QUESTION = 4
MAX_SECTION_MINUTES = 30
EMPTY_SECTION_MINUTES = 5
SECONDS_PER_FLASHCARD = 20
MIN_FLASHCARD_MINUTES = 5
MIN_QUICKKICK_SECONDS = 180
QUICKKICK_QUESTION_SECONDS = 120
DEFAULT_CUSTOM_MINUTES = 15


def _minutes(seconds):
    return max(1, int(math.ceil(seconds / 60)))


def exam_part_marks(part):
    """A part's marks, or a defensible stand-in.

    ``ExamQuestionPart.max_marks`` is nullable until someone fills it in, so
    fall back to what its siblings are worth, then to an even split of the
    question, then to a flat ten.
    """
    if part.max_marks:
        return part.max_marks
    siblings = [p.max_marks for p in part.question.parts.all() if p.max_marks]
    if siblings:
        return round(sum(siblings) / len(siblings))
    total = part.question.total_marks
    count = part.question.parts.count() or 1
    if total:
        return max(1, round(total / count))
    return DEFAULT_EXAM_PART_MARKS


def exam_part_minutes(part):
    return _minutes(exam_part_marks(part) * SECONDS_PER_MARK)


def exam_question_minutes(question):
    seconds = question.suggested_time_seconds
    if seconds:
        return _minutes(seconds)
    return DEFAULT_EXAM_QUESTION_MINUTES


def section_minutes(section, question_count=None):
    count = (question_count if question_count is not None
             else section.questions.count())
    if not count:
        return EMPTY_SECTION_MINUTES
    return min(MAX_SECTION_MINUTES, count * MINUTES_PER_SECTION_QUESTION)


def flashcard_set_minutes(flashcard_set, card_count=None):
    count = card_count if card_count is not None else flashcard_set.card_count()
    return max(MIN_FLASHCARD_MINUTES, _minutes(count * SECONDS_PER_FLASHCARD))


def quickkick_minutes(quickkick):
    seconds = max(quickkick.duration_seconds or 0, MIN_QUICKKICK_SECONDS)
    if quickkick.question_id:
        seconds += QUICKKICK_QUESTION_SECONDS
    return _minutes(seconds)


def minutes_for(kind, obj):
    """Minutes for any content unit, dispatched on its kind."""
    if obj is None:
        return DEFAULT_CUSTOM_MINUTES
    if kind == 'exam_part':
        return exam_part_minutes(obj)
    if kind == 'exam_question':
        return exam_question_minutes(obj)
    if kind == 'section':
        return section_minutes(obj)
    if kind == 'flashcard':
        return flashcard_set_minutes(obj)
    if kind == 'quickkick':
        return quickkick_minutes(obj)
    return DEFAULT_CUSTOM_MINUTES
