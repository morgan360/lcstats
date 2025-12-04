from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from interactive_lessons.models import Topic
from .models import CheatSheet


@login_required
def cheatsheets_index(request):
    """
    Display all cheat sheets across all topics.
    """
    cheatsheets = CheatSheet.objects.select_related('topic').order_by('topic__name', 'order', 'title')

    context = {
        'cheatsheets': cheatsheets,
    }
    return render(request, 'cheatsheets/index.html', context)


@login_required
def cheatsheets_by_topic(request, topic_slug):
    """
    Display all cheat sheets for a specific topic.
    Each PDF can be opened in a new tab.
    """
    topic = get_object_or_404(Topic, slug=topic_slug)
    cheatsheets = CheatSheet.objects.filter(topic=topic).order_by('order', 'title')

    context = {
        'topic': topic,
        'cheatsheets': cheatsheets,
    }

    return render(request, 'cheatsheets/cheatsheets_list.html', context)
