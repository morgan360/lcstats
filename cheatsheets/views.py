from django.shortcuts import render, get_object_or_404
from interactive_lessons.models import Topic
from .models import CheatSheet


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
