"""Shaping a plan into what the student's progress card shows.

The card leads with topics mastered rather than tasks ticked, because ticking a
task only says work happened. Passing a checkpoint says it worked. Tasks done
still appear, underneath, as the way in to this week's work.
"""
from django.utils import timezone

from ..models import StudyPlan

#: Ordering for the card: what needs doing first, what is finished last.
STATE_ORDER = {
    'ready': 0,      # a checkpoint waiting to be sat
    'retry': 1,      # failed, more work added
    'working': 2,
    'not_started': 3,
    'blocked': 4,
    'mastered': 5,
}


def goal_state(goal):
    """One goal as the card sees it."""
    items = [i for i in goal.items.all() if i.status != 'skipped']
    done = sum(1 for i in items if i.status == 'done')
    latest = goal.checkpoints.order_by('-round').first()

    if goal.mastered_at:
        state = 'mastered'
    elif latest and latest.status == 'ready':
        state = 'ready'
    elif latest and latest.status == 'failed':
        state = 'retry'
    elif goal.needs_teacher_attention:
        state = 'blocked'
    elif done:
        state = 'working'
    else:
        state = 'not_started'

    return {
        'goal': goal,
        'topic': goal.topic,
        'state': state,
        'items_done': done,
        'items_total': len(items),
        'percent': int(100 * done / len(items)) if items else 0,
        'checkpoint': latest,
        'score': goal.mastery_score,
        'mastered_at': goal.mastered_at,
    }


def plan_card(plan):
    """Everything the progress card needs, in one shape."""
    goals = (plan.goals
             .select_related('topic')
             .prefetch_related('items', 'checkpoints'))
    states = [goal_state(goal) for goal in goals]
    states.sort(key=lambda s: (STATE_ORDER[s['state']], s['topic'].name))
    mastered = sum(1 for s in states if s['state'] == 'mastered')

    return {
        'plan': plan,
        'goals': states,
        'mastered': mastered,
        'total': len(states),
        'percent': int(100 * mastered / len(states)) if states else 0,
        'days_remaining': plan.days_remaining,
        'ready_count': sum(1 for s in states if s['state'] == 'ready'),
    }


def active_plan_for(user, subject=None):
    """The plan a student is working on now, if any."""
    plans = StudyPlan.objects.filter(student=user, status='active')
    if subject is not None:
        by_subject = plans.filter(subject=subject)
        if by_subject.exists():
            plans = by_subject
    return plans.select_related('subject', 'teacher').first()


def week_view(plan, week):
    """One week's items, with the links and labels the template needs."""
    if week is None:
        return {'week': None, 'items': [], 'minutes_total': 0, 'minutes_done': 0}
    items = list(week.items.select_related(
        'goal__topic', 'section__topic', 'exam_question__exam_paper',
        'exam_question_part__question__exam_paper', 'quickkick__topic',
        'flashcard_set__topic').order_by('order', 'id'))
    visible = [i for i in items if i.status != 'skipped']
    return {
        'week': week,
        'items': visible,
        'minutes_total': sum(i.estimated_minutes for i in visible),
        'minutes_done': sum(i.estimated_minutes for i in visible
                            if i.status == 'done'),
    }


def achievements_for(user):
    """Every checkpoint this student has ever passed, newest first.

    Reads the frozen result off the checkpoint rather than recomputing, so an
    achievement stays exactly as it was earned even if the exam parts behind it
    are later edited or merged.
    """
    from ..models import StudyPlanCheckpoint

    passed = (StudyPlanCheckpoint.objects
              .filter(goal__plan__student=user, status='passed')
              .select_related('goal__topic__subject', 'goal__plan')
              .order_by('-sat_at'))

    by_subject = {}
    for checkpoint in passed:
        subject = checkpoint.goal.topic.subject
        key = subject.name if subject else 'Other'
        by_subject.setdefault(key, []).append(checkpoint)

    return {
        'total': passed.count(),
        'by_subject': sorted(by_subject.items()),
        'best': max((c.score for c in passed if c.score is not None), default=None),
        'latest': passed.first(),
    }
