"""The nav badge for study plans.

This runs on every render of every page, including the error pages, so it
swallows its own exceptions the way homework.context_processors does. A badge is
never worth a 500.
"""
import logging

logger = logging.getLogger(__name__)


def study_plan_count(request):
    """Work left in each topic's next MicroBadge, plus any Badge Test to sit.

    A ready Badge Test is counted because it is the thing most worth coming back
    for -- the student has done the work and the topic is one sitting from done.
    """
    if not request.user.is_authenticated or request.user.is_staff:
        return {'study_plan_badge_count': 0}

    try:
        from .models import StudyPlanCheckpoint, StudyPlanGoal
        from .services import microbadges

        goals = list(StudyPlanGoal.objects
                     .filter(plan__student=request.user, plan__status='active',
                             mastered_at__isnull=True)
                     .prefetch_related('micro_badges__items'))
        if not goals:
            return {'study_plan_badge_count': 0}

        due = 0
        for goal in goals:
            badge = microbadges.next_badge(goal)
            if badge is not None:
                due += sum(1 for i in badge.live_items() if i.status != 'done')

        ready = StudyPlanCheckpoint.objects.filter(
            goal__in=goals, status='ready').count()

        return {'study_plan_badge_count': due + ready}
    except Exception as exc:
        logger.error("Error in study_plan_count context processor: %s", exc,
                     exc_info=True)
        return {'study_plan_badge_count': 0}
