from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import HWSolution


def _is_teacher(user):
    """Teachers' accounts are staff (a teacher registration code makes one)."""
    return user.is_staff


@login_required
def hw_solutions_index(request):
    """
    List every homework solution PDF for the current subject. Solutions with no
    subject set are shown under every subject.

    Students see only released sheets. Teachers see them all, each with its
    release tick box.
    """
    solutions = HWSolution.objects.select_related('subject')

    current_subject = getattr(request, 'current_subject', None)
    if current_subject:
        solutions = solutions.filter(
            Q(subject=current_subject) | Q(subject__isnull=True)
        )

    is_teacher = _is_teacher(request.user)
    if not is_teacher:
        solutions = solutions.filter(is_released=True)

    return render(request, 'hw_solutions/index.html', {
        'solutions': solutions,
        'current_subject': current_subject,
        'is_teacher': is_teacher,
    })


@login_required
@require_POST
def set_released(request, solution_id):
    """Tick or untick a sheet's release. Checked here, not just hidden."""
    if not _is_teacher(request.user):
        return HttpResponseForbidden("Teachers only.")
    solution = get_object_or_404(HWSolution, pk=solution_id)
    solution.is_released = request.POST.get('released') == '1'
    solution.save(update_fields=['is_released', 'updated_at'])
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'released': solution.is_released})
    return redirect('hw_solutions:hw_solutions_index')
