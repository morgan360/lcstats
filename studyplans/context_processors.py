"""The nav badge for study plans.

This runs on every render of every page, including the error pages, so it
swallows its own exceptions the way homework.context_processors does. A badge is
never worth a 500.
"""
import logging

from django.utils import timezone

logger = logging.getLogger(__name__)


def study_plan_count(request):
    """Work due this week, plus any checkpoint waiting to be sat.

    A ready checkpoint is counted because it is the thing most worth coming back
    for -- the student has done the work and the topic is one sitting from done.
    """
    if not request.user.is_authenticated or request.user.is_staff:
        return {'study_plan_badge_count': 0}

    try:
        from .models import StudyPlan, StudyPlanCheckpoint, StudyPlanItem

        plan_ids = list(
            StudyPlan.objects
            .filter(student=request.user, status='active')
            .values_list('id', flat=True)
        )
        if not plan_ids:
            return {'study_plan_badge_count': 0}

        today = timezone.localdate()
        due = StudyPlanItem.objects.filter(
            plan_id__in=plan_ids,
            status__in=('pending', 'attempted'),
            available_from__lte=today,
            due_date__gte=today,
        ).count()

        ready = StudyPlanCheckpoint.objects.filter(
            goal__plan_id__in=plan_ids, status='ready',
        ).count()

        return {'study_plan_badge_count': due + ready}
    except Exception as exc:
        logger.error("Error in study_plan_count context processor: %s", exc,
                     exc_info=True)
        return {'study_plan_badge_count': 0}
