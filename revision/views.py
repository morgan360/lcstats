from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Prefetch
from .models import RevisionModule, RevisionSection


@login_required
def module_list(request):
    """Display list of all published revision modules"""
    modules = RevisionModule.objects.filter(
        is_published=True
    ).select_related('topic').annotate(
        section_count=Count('sections')
    ).order_by('order', 'title')

    context = {
        'modules': modules,
        'page_title': 'Revision Modules'
    }
    return render(request, 'revision/module_list.html', context)


@login_required
def module_detail(request, topic_slug):
    """Display a specific revision module with all its sections"""
    module = get_object_or_404(
        RevisionModule.objects.select_related('topic').prefetch_related(
            Prefetch('sections', queryset=RevisionSection.objects.order_by('order'))
        ),
        topic__slug=topic_slug,
        is_published=True
    )

    context = {
        'module': module,
        'sections': module.sections.all(),
        'page_title': f'Revision: {module.title}'
    }
    return render(request, 'revision/module_detail.html', context)
