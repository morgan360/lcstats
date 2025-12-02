from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from interactive_lessons.models import Topic
from .models import QuickKick


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
    """
    topic = get_object_or_404(Topic, slug=topic_slug)
    quickkick = get_object_or_404(QuickKick, id=quickkick_id, topic=topic)

    context = {
        'topic': topic,
        'quickkick': quickkick,
    }
    return render(request, 'quickkicks/quickkick_view.html', context)
