from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from interactive_lessons.models import Topic
from .models import QuickKick, QuickKickView


@login_required
def quickkicks_index(request):
    """
    Display all QuickKick videos across all topics.
    """
    quickkicks = QuickKick.objects.select_related('topic').order_by('topic__name', 'order', 'title')

    context = {
        'quickkicks': quickkicks,
    }
    return render(request, 'quickkicks/index.html', context)


@login_required
def quickkicks_list(request, topic_slug):
    """
    Display all QuickKick videos for a specific topic.
    Replaces the Revision column in interactive lessons.
    """
    topic = get_object_or_404(Topic, slug=topic_slug)
    quickkicks = QuickKick.objects.filter(topic=topic).order_by('order', 'title')

    context = {
        'topic': topic,
        'quickkicks': quickkicks,
    }
    return render(request, 'quickkicks/quickkicks_list.html', context)


@login_required
def quickkick_view(request, topic_slug, quickkick_id):
    """
    Display a single QuickKick video for watching.
    Records the view for homework tracking.
    """
    topic = get_object_or_404(Topic, slug=topic_slug)
    quickkick = get_object_or_404(QuickKick, id=quickkick_id, topic=topic)

    # Track that this user viewed this QuickKick
    QuickKickView.objects.get_or_create(
        user=request.user,
        quickkick=quickkick
    )

    context = {
        'topic': topic,
        'quickkick': quickkick,
    }
    return render(request, 'quickkicks/quickkick_view.html', context)
