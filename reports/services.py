"""
Aggregation of automatic NumScoil activity (question attempts, homework tasks,
flashcards, quickkicks, exam attempts) for teacher reports.

Both public functions take the whole roster at once and run exactly one query
per activity source (5 total) — never per student.
"""
from collections import defaultdict

from django.db.models import Count, DateTimeField
from django.db.models.functions import Coalesce, TruncDate

from exam_papers.models import ExamAttempt
from flashcards.models import FlashcardAttempt
from homework.models import StudentHomeworkProgress
from quickkicks.models import QuickKickView
from students.models import QuestionAttempt

# Each source: (report key, queryset builder taking user_ids, timestamp expression
# name, path to the user id in values()).
# QuestionAttempt is the odd one out: its student FK points at StudentProfile,
# so the user id is reached through student__user_id.


def _sources(user_ids):
    return [
        (
            'questions',
            QuestionAttempt.objects.filter(student__user_id__in=user_ids),
            'attempted_at',
            'student__user_id',
        ),
        (
            'homework_tasks',
            StudentHomeworkProgress.objects.filter(student_id__in=user_ids, is_completed=True),
            'completed_at',
            'student_id',
        ),
        (
            'flashcards',
            FlashcardAttempt.objects.filter(student_id__in=user_ids).annotate(
                activity_ts=Coalesce('last_answered_at', 'created_at', output_field=DateTimeField())
            ),
            'activity_ts',
            'student_id',
        ),
        (
            'quickkicks',
            QuickKickView.objects.filter(user_id__in=user_ids),
            'viewed_at',
            'user_id',
        ),
        (
            'exams',
            ExamAttempt.objects.filter(student_id__in=user_ids),
            'started_at',
            'student_id',
        ),
    ]


def get_activity_by_day(students, start_dt, end_dt):
    """
    Per-day activity counts per student across all five sources.

    Returns {user_id: {date: {'questions': n, 'homework_tasks': n, 'flashcards': n,
                              'quickkicks': n, 'exams': n, 'total': n}}}.
    Days with no activity are absent from the inner dict.
    """
    user_ids = [getattr(s, 'id', s) for s in students]
    result = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))

    for key, qs, ts_field, user_path in _sources(user_ids):
        rows = (
            qs.filter(**{f'{ts_field}__range': (start_dt, end_dt)})
            .annotate(day=TruncDate(ts_field))
            .values(user_path, 'day')
            .annotate(n=Count('id'))
        )
        for row in rows:
            day_counts = result[row[user_path]][row['day']]
            day_counts[key] += row['n']
            day_counts['total'] += row['n']

    # Plain dicts out (defaultdict surprises templates)
    return {
        uid: {day: dict(counts) for day, counts in days.items()}
        for uid, days in result.items()
    }


def user_ids_active_since(students, since_dt):
    """User ids (from the given students) with any recorded activity since since_dt."""
    user_ids = [getattr(s, 'id', s) for s in students]
    active = set()
    for _key, qs, ts_field, user_path in _sources(user_ids):
        active.update(
            qs.filter(**{f'{ts_field}__gte': since_dt})
            .values_list(user_path, flat=True)
            .distinct()
        )
    return active


def activity_totals(activity_by_day, user_id):
    """Sum one student's per-day dict from get_activity_by_day into overall totals."""
    totals = defaultdict(int)
    for counts in activity_by_day.get(user_id, {}).values():
        for key, n in counts.items():
            totals[key] += n
    return dict(totals)
