from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseNotFound
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


@login_required
def log_tables_view(request):
    """
    Quick access view for log tables cheatsheet.
    Redirects directly to the log tables PDF if it exists.
    Falls back to general cheatsheets page if not found.
    """
    try:
        # Look for a cheatsheet with "log" and "table" in the title
        log_tables = CheatSheet.objects.filter(
            title__icontains='log'
        ).filter(
            title__icontains='table'
        ).first()

        if log_tables and log_tables.pdf_file:
            # Redirect to the PDF file directly
            return redirect(log_tables.pdf_file.url)
        else:
            # If not found, go to cheatsheets index
            return redirect('cheatsheets:cheatsheets_index')
    except Exception:
        return redirect('cheatsheets:cheatsheets_index')
