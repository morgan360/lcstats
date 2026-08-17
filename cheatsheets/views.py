from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseNotFound
from interactive_lessons.models import Topic
from .models import CheatSheet
from . import log_tables_index


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


def get_log_tables_cheatsheet():
    """The Formulae and Tables booklet, or None if it has not been uploaded."""
    return CheatSheet.objects.filter(
        title__icontains='log'
    ).filter(
        title__icontains='table'
    ).first()


@login_required
def log_tables_view(request):
    """
    The log tables booklet, opening on its own contents spread with the contents
    rows made clickable. Deliberately the same for every student: no topic or
    subject steering, so they learn the booklet itself.

    ?page= takes a printed booklet page number, so a teacher can point at
    /cheatsheets/log-tables/?page=33 in class.
    Falls back to the cheatsheets index if the booklet has not been uploaded.
    """
    log_tables = get_log_tables_cheatsheet()

    if not log_tables or not log_tables.pdf_file:
        return redirect('cheatsheets:cheatsheets_index')

    start_pdf_page = log_tables_index.CONTENTS_PDF_PAGE
    requested_page = request.GET.get('page')
    if requested_page:
        try:
            printed_page = int(requested_page)
        except ValueError:
            pass
        else:
            if log_tables_index.FIRST_PRINTED_PAGE <= printed_page <= log_tables_index.LAST_PRINTED_PAGE:
                start_pdf_page = log_tables_index.to_pdf_page(printed_page)

    context = log_tables_index.viewer_context(log_tables.pdf_file.url, start_pdf_page)
    return render(request, 'cheatsheets/log_tables.html', context)
