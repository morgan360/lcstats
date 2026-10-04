from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseNotFound
from interactive_lessons.models import Topic
from .models import CheatSheet
from . import log_tables_index


def _sheets_for_subject(request, kind):
    """One kind of sheet, for the subject the session is in."""
    sheets = CheatSheet.objects.filter(kind=kind).select_related('topic')
    current_subject = getattr(request, 'current_subject', None)
    if current_subject:
        sheets = sheets.filter(topic__subject=current_subject)
    return sheets


def _grouped_by_topic(sheets):
    """[(topic, [sheet, ...]), ...] in the topic order the Exercises page uses."""
    groups = {}
    for sheet in sheets.order_by('topic__order', 'topic__name', 'order', 'title'):
        groups.setdefault(sheet.topic, []).append(sheet)
    return list(groups.items())


def _sheet_index(request, kind, heading, intro):
    return render(request, 'cheatsheets/index.html', {
        'heading': heading,
        'intro': intro,
        'topic_groups': _grouped_by_topic(_sheets_for_subject(request, kind)),
    })


@login_required
def cheatsheets_index(request):
    """The two-page cheat sheets, one per topic."""
    return _sheet_index(
        request, CheatSheet.KIND_CHEAT_SHEET, 'Cheat Sheets',
        'Two A4 pages per topic: the formulae, methods and exam traps to know.',
    )


@login_required
def summary_notes_index(request):
    """The summary notes, one section of the notes per topic."""
    return _sheet_index(
        request, CheatSheet.KIND_SUMMARY_NOTES, 'Summary Notes',
        'The notes for each topic, with worked examples and proofs.',
    )


@login_required
def cheatsheets_by_topic(request, topic_slug):
    """A topic's Summary Notes and Cheat Sheet, each under its own heading."""
    topic = get_object_or_404(Topic, slug=topic_slug)
    sheets = CheatSheet.objects.filter(topic=topic).order_by('order', 'title')

    context = {
        'topic': topic,
        'sections': [
            ('Summary Notes', sheets.filter(kind=CheatSheet.KIND_SUMMARY_NOTES)),
            ('Cheat Sheet', sheets.filter(kind=CheatSheet.KIND_CHEAT_SHEET)),
        ],
    }

    return render(request, 'cheatsheets/cheatsheets_list.html', context)


def get_log_tables_cheatsheet():
    """The Formulae and Tables booklet, or None if it has not been uploaded."""
    reference = CheatSheet.objects.filter(kind=CheatSheet.KIND_REFERENCE)
    # Fall back to the title for a row added before the kind field existed.
    return (
        reference.filter(title__icontains='log').first()
        or CheatSheet.objects.filter(title__icontains='log').filter(title__icontains='table').first()
    )


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
