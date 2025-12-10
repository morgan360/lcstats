from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


def homework_count(request):
    """
    Add homework count to template context for badge display.
    """
    if not request.user.is_authenticated or request.user.is_staff:
        return {'homework_badge_count': 0}

    try:
        # Import here to avoid circular import issues
        from .models import HomeworkAssignment, HomeworkSubmission

        # Get all assignments for this student
        class_assignments = HomeworkAssignment.objects.filter(
            assigned_classes__students=request.user,
            is_published=True
        )
        individual_assignments = HomeworkAssignment.objects.filter(
            assigned_students=request.user,
            is_published=True
        )
        all_assignments = (class_assignments | individual_assignments).distinct()

        # Count unsubmitted assignments
        count = 0
        for assignment in all_assignments:
            has_submitted = HomeworkSubmission.objects.filter(
                student=request.user,
                assignment=assignment
            ).exists()
            if not has_submitted:
                count += 1

        return {'homework_badge_count': count}
    except Exception as e:
        # Log the error for debugging on PythonAnywhere
        logger.error(f"Error in homework_count context processor: {e}", exc_info=True)
        return {'homework_badge_count': 0}
