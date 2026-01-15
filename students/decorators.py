"""
Permission decorators for group-based access control.

Usage:
    @group_required('Teachers')
    def teacher_only_view(request):
        ...

    @group_required('Students', 'Teachers')  # Allow multiple groups
    def student_or_teacher_view(request):
        ...
"""
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages


def group_required(*group_names):
    """
    Decorator to restrict view access to users in specific groups.

    Args:
        *group_names: One or more group names (e.g., 'Students', 'Teachers')

    Returns:
        Decorated view function that checks group membership

    Raises:
        PermissionDenied: If user is not in any of the specified groups

    Example:
        @group_required('Teachers')
        def teacher_dashboard(request):
            return render(request, 'teacher_dashboard.html')
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            # Check if user is in any of the specified groups
            if request.user.groups.filter(name__in=group_names).exists():
                return view_func(request, *args, **kwargs)

            # User is not in any of the allowed groups
            messages.error(request, 'You do not have permission to access this page.')
            raise PermissionDenied

        return wrapper
    return decorator


def teacher_required(view_func):
    """
    Decorator to restrict view access to teachers only.
    Shorthand for @group_required('Teachers')

    Example:
        @teacher_required
        def create_homework(request):
            return render(request, 'homework/create.html')
    """
    return group_required('Teachers')(view_func)


def student_required(view_func):
    """
    Decorator to restrict view access to students only.
    Shorthand for @group_required('Students')

    Example:
        @student_required
        def student_dashboard(request):
            return render(request, 'students/dashboard.html')
    """
    return group_required('Students')(view_func)


def student_or_teacher_required(view_func):
    """
    Decorator to restrict view access to students or teachers.
    Shorthand for @group_required('Students', 'Teachers')

    Example:
        @student_or_teacher_required
        def shared_view(request):
            return render(request, 'shared.html')
    """
    return group_required('Students', 'Teachers')(view_func)