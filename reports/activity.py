"""Everything students did on the site on one day, gathered into one timeline.

Read-only: every source below already records when it happened, so this only
collects rows and never adds tracking of its own. A day is a calendar day in
Europe/Dublin, the site's TIME_ZONE, and is filtered as a datetime range
rather than with __date so it does not lean on MySQL's timezone tables.

Flashcards are the one approximate source: FlashcardAttempt keeps a single
row per student per card, with only the latest answer's time, so a card
answered twice today appears once.
"""
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta

from django.contrib.auth.models import User
from django.utils import timezone

from exam_papers.models import ExamQuestionAttempt
from flashcards.models import FlashcardAttempt
from homework.models import HomeworkSubmission, StudentHomeworkProgress
from quickkicks.models import QuickKickView
from students.models import LoginHistory, QuestionAttempt, WorkSubmission
from studyplans.models import StudyPlanCheckpoint, StudyPlanMicroBadge

# (key, label) in the order the summary tiles and per-student counts show them.
KINDS = [
    ('login', 'Logins'),
    ('lesson', 'Lesson answers'),
    ('exam', 'Exam part answers'),
    ('flashcard', 'Flashcards'),
    ('photo', 'Work photos'),
    ('microbadge', 'MicroBadges'),
    ('badge_test', 'Badge Tests'),
    ('homework', 'Homework'),
    ('quickkick', 'QuickFlicks'),
]


@dataclass
class Event:
    when: datetime
    kind: str
    text: str
    outcome: str = ''   # 'good', 'bad' or '' - colours the row


@dataclass
class StudentDay:
    user: User
    events: list = field(default_factory=list)

    @property
    def first(self):
        return self.events[0].when

    @property
    def last(self):
        return self.events[-1].when

    @property
    def counts(self):
        tally = {}
        for event in self.events:
            tally[event.kind] = tally.get(event.kind, 0) + 1
        return [(label, tally[key]) for key, label in KINDS if key in tally]


def day_bounds(day):
    """[start, end) of a local calendar day, as aware datetimes."""
    tz = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.combine(day, time.min), tz)
    end = timezone.make_aware(datetime.combine(day + timedelta(days=1), time.min), tz)
    return start, end


def _marks(awarded, possible):
    return f'{awarded:g}/{possible:g}'


def _events(start, end):
    """(user, Event) pairs from every source, in no particular order."""
    span = {'__gte': start, '__lt': end}

    def within(name):
        return {name + k: v for k, v in span.items()}

    for row in (LoginHistory.objects.filter(**within('timestamp'), success=True)
                .select_related('user')):
        if row.user:
            yield row.user, Event(row.timestamp, 'login', 'Logged in')

    for row in (QuestionAttempt.objects.filter(**within('attempted_at'))
                .select_related('student__user', 'question__topic',
                                'question__section', 'question_part')):
        question = row.question
        where = question.topic.name
        if question.section:
            where += f' - {question.section.name}'
        part = f' {row.question_part.label}' if row.question_part else ''
        yield row.student.user, Event(
            row.attempted_at, 'lesson', f'{where}: Q{question.order}{part}',
            'good' if row.is_correct else 'bad')

    for row in (ExamQuestionAttempt.objects.filter(**within('submitted_at'))
                .select_related('exam_attempt__student',
                                'question_part__question__exam_paper')):
        extras = [x for x, used in (('hint', row.hint_used),
                                    ('solution', row.solution_viewed)) if used]
        note = f' (used {" and ".join(extras)})' if extras else ''
        yield row.exam_attempt.student, Event(
            row.submitted_at, 'exam',
            f'{row.question_part} - {_marks(row.marks_awarded, row.max_marks)}{note}',
            'good' if row.is_correct else 'bad')

    for row in (FlashcardAttempt.objects.filter(**within('last_answered_at'))
                .select_related('student', 'flashcard__flashcard_set')):
        yield row.student, Event(
            row.last_answered_at, 'flashcard',
            f'{row.flashcard.flashcard_set.title} card - now {row.get_mastery_level_display()}',
            'good' if row.last_answer_correct else 'bad')

    for row in (WorkSubmission.objects.filter(**within('created_at'))
                .select_related('student__user', 'exam_question_part__question__exam_paper',
                                'question_part')):
        target = row.exam_question_part or row.question_part
        yield row.student.user, Event(
            row.created_at, 'photo',
            f'Photographed working{f" for {target}" if target else ""}')

    for row in (StudyPlanMicroBadge.objects.filter(**within('earned_at'))
                .select_related('goal__plan__student', 'goal__topic')):
        by = ' (awarded by teacher)' if row.earned_by_teacher else ''
        yield row.goal.plan.student, Event(
            row.earned_at, 'microbadge',
            f'Earned {row.goal.topic.name} MicroBadge {row.number}{by}', 'good')

    for row in (StudyPlanCheckpoint.objects.filter(**within('sat_at'))
                .select_related('goal__plan__student', 'goal__topic')):
        score = f' - {row.score:.0f}%' if row.score is not None else ''
        yield row.goal.plan.student, Event(
            row.sat_at, 'badge_test',
            f'Sat {row.goal.topic.name} Badge Test {row.round}: '
            f'{row.get_status_display()}{score}',
            {'passed': 'good', 'failed': 'bad'}.get(row.status, ''))

    for row in (StudentHomeworkProgress.objects.filter(**within('completed_at'),
                                                       is_completed=True)
                .select_related('student', 'assignment')):
        yield row.student, Event(
            row.completed_at, 'homework',
            f'Completed a task in "{row.assignment.title}"', 'good')

    for row in (HomeworkSubmission.objects.filter(**within('submitted_at'))
                .select_related('student', 'assignment')):
        late = ' (late)' if row.is_late else ''
        yield row.student, Event(
            row.submitted_at, 'homework',
            f'Submitted "{row.assignment.title}"{late}', 'bad' if late else 'good')

    for row in (QuickKickView.objects.filter(**within('viewed_at'))
                .select_related('user', 'quickkick')):
        yield row.user, Event(row.viewed_at, 'quickkick',
                              f'Watched "{row.quickkick.title}"')


def activity_for_day(day, include_staff=False):
    """The day's activity: per-student timelines, totals, and failed logins.

    Students come most recently active first; each timeline runs in time order.
    """
    start, end = day_bounds(day)
    students = {}
    for user, event in _events(start, end):
        if user.is_staff and not include_staff:
            continue
        students.setdefault(user.pk, StudentDay(user)).events.append(event)

    for student in students.values():
        student.events.sort(key=lambda e: e.when)
    ordered = sorted(students.values(), key=lambda s: s.last, reverse=True)

    totals = OrderedDict((label, 0) for _, label in KINDS)
    for student in ordered:
        for label, count in student.counts:
            totals[label] += count

    failed_logins = list(LoginHistory.objects.filter(
        timestamp__gte=start, timestamp__lt=end, success=False
    ).order_by('-timestamp'))

    return {
        'students': ordered,
        'totals': [(label, n) for label, n in totals.items() if n],
        'failed_logins': failed_logins,
    }
