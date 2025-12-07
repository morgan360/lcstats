from .views import get_homework_summary


def homework_count(request):
    """
    Add homework count to template context for badge display.
    """
    if request.user.is_authenticated and not request.user.is_staff:
        try:
            summary = get_homework_summary(request.user)
            return {'homework_badge_count': summary['total_count']}
        except:
            return {'homework_badge_count': 0}
    return {'homework_badge_count': 0}
