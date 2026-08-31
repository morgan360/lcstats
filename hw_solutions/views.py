from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render

from .models import HWSolution


@login_required
def hw_solutions_index(request):
    """
    List every homework solution PDF for the current subject. Solutions with no
    subject set are shown under every subject.
    """
    solutions = HWSolution.objects.select_related('subject')

    current_subject = getattr(request, 'current_subject', None)
    if current_subject:
        solutions = solutions.filter(
            Q(subject=current_subject) | Q(subject__isnull=True)
        )

    return render(request, 'hw_solutions/index.html', {
        'solutions': solutions,
        'current_subject': current_subject,
    })
