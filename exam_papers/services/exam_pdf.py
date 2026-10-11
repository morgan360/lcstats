"""A teacher's exam as two PDFs: the paper to sit, and its marking scheme.

Built on the worksheet's page filler, with what a paper to hand out needs on
top: a cover page with a marks grid, every question on a fresh page and
renumbered 1, 2, 3, and the exam's title and page numbers on every page after
the cover.

Renumbering means hiding the paper's own number. Each question image is a crop
of the SEC paper, and it starts with the printed line "Question 6 ... (30
marks)"; left in, a student would read "Question 2" over "Question 6" and could
look the question up. So the crop is trimmed to start just below that line,
which also takes off a "Section A" banner above it when there is one.
"""
import numpy as np
import fitz

from .worksheet_pdf import (
    GAP, LINE_HEIGHT, MARGIN, PAGE_HEIGHT, PAGE_WIDTH,
    _Sheet, _image_path, _prepare_image, _scheme_crops,
)

INK_LEVEL = 200

# The printed heading is one line: "Question N" at the left margin, "(N marks)"
# at the right, nothing between. Checked against all 350 question crops on the
# live site: it matched the real heading in 340, including those with a Section
# banner above, and none of the 10 it missed has such a line to remove (2012
# Paper 1 prints "1. (a) ..." inline; two others start mid-question or put a
# diagram beside the heading). Those are left whole: better a stray number than
# a lost line of the question.
HEADING_SEARCH = 0.25        # look in the top quarter of the crop
HEADING_BANDS = 5            # and at no more than its first five lines
LINE_MIN, LINE_MAX = 0.008, 0.04   # a line's height, as a fraction of the width
LEFT_EDGE, RIGHT_EDGE, MIDDLE_GAP = 0.25, 0.7, 0.35
BAND_MERGE_PX = 6            # blank rows inside one line of print (e.g. under a 'Q')

HEADER_SIZE = 8
FOOTER_SIZE = 9
GREY = (0.4, 0.4, 0.4)


def _ink_bands(gray, max_rows):
    """(top, bottom) of each line of print in the first max_rows rows."""
    inked = gray[:max_rows].min(axis=1) < INK_LEVEL
    bands, start, last = [], None, None
    for y, ink in enumerate(inked):
        if not ink:
            continue
        if start is None:
            start = y
        elif y - last > BAND_MERGE_PX:
            bands.append((start, last + 1))
            start = y
        last = y
    if start is not None:
        bands.append((start, last + 1))
    return bands


def printed_heading_bottom(img):
    """The row just below the paper's "Question N (N marks)" line, or None."""
    gray = np.asarray(img.convert('L'))
    height, width = gray.shape
    for top, bottom in _ink_bands(gray, int(height * HEADING_SEARCH))[:HEADING_BANDS]:
        if not LINE_MIN * width < bottom - top < LINE_MAX * width:
            continue
        cols = np.where(gray[top:bottom].min(axis=0) < INK_LEVEL)[0]
        if len(cols) < 2:
            continue
        if (cols[0] < LEFT_EDGE * width and cols[-1] > RIGHT_EDGE * width
                and np.diff(cols).max() > MIDDLE_GAP * width):
            return bottom
    return None


# Each crop is a stack of whole A4 pages, and every page ends with the SEC
# footer: "Leaving Certificate 2019 / Mathematics, Paper 1" and a page number,
# with a barcode above it on 2019's. That names the source as plainly as the
# heading does. Measured over every page of every crop on the live site
# (2012-2026): the footer is always the last line or two of print, starting at
# 0.930-0.960 of the page height (the 2019 barcode at 0.913), while answer
# grids above it end by 0.943 with a gap before the footer. So the trailing
# lines starting below FOOTER_TOP are the footer; a page whose last line starts
# higher (a diagram running to the edge) is left alone.
A4_RATIO = 297 / 210
FOOTER_TOP = 0.91


def _whole_pages(img):
    """How many A4 pages the crop is, or None if it is not a whole number of them."""
    pages = img.height / (img.width * A4_RATIO)
    count = round(pages)
    return count if count and abs(pages - count) < 0.01 else None


def footer_cuts(img):
    """[(top, bottom)] of each page's footer, in image rows."""
    count = _whole_pages(img)
    if not count:
        return []
    gray = np.asarray(img.convert('L'))
    page_h = img.height / count
    cuts = []
    for p in range(count):
        page_top, page_end = round(p * page_h), round((p + 1) * page_h)
        search = page_top + round(page_h * 0.85)
        lines = [(search + a, search + b) for a, b in _ink_bands(gray[search:page_end], page_end - search)]
        footer = []
        while lines and lines[-1][0] - page_top >= FOOTER_TOP * page_h:
            footer.insert(0, lines.pop())
        if not footer:
            continue
        above = lines[-1][1] if lines else footer[0][0] - 4
        cuts.append(((above + footer[0][0]) // 2, page_end))
    return cuts


def without_page_footers(img):
    """The crop with every page's SEC footer painted out."""
    cuts = footer_cuts(img)
    if not cuts:
        return img
    img = img.copy()
    for top, bottom in cuts:
        img.paste((255, 255, 255), (0, top, img.width, bottom))
    return img


# The last question on the 2012-2014 papers carries the paper's back page: a
# full-page spare grid with "Leaving Certificate 2013 - Higher Level /
# Mathematics (Project Maths - Phase 2) - Paper 1 / Friday 7 June" under it.
# It belongs to no question, and the title block sits too high to be taken for
# a footer, so the whole page goes. A last page counts as spare when nothing
# above SPARE_PAGE_TOP of it is anything but one grid from the top (or nothing).
SPARE_PAGE_TOP = 0.78


def without_spare_last_page(img):
    """The crop without a trailing spare-grid page; unchanged if it has none."""
    count = _whole_pages(img)
    if not count or count < 2:
        return img
    page_h = img.height / count
    start = round((count - 1) * page_h)
    gray = np.asarray(img.convert('L'))
    lines = _ink_bands(gray[start:], round(page_h * SPARE_PAGE_TOP))
    spare = not lines or (len(lines) == 1 and lines[0][0] < 0.1 * page_h
                          and lines[0][1] >= 0.75 * page_h)
    return img.crop((0, 0, img.width, start)) if spare else img


def without_printed_heading(img):
    """The crop starting below its printed heading; unchanged if there is none."""
    bottom = printed_heading_bottom(img)
    if bottom is None:
        return img
    return img.crop((0, bottom, img.width, img.height))


def _students_copy(img):
    """The crop with everything that names its source taken off."""
    return without_printed_heading(without_page_footers(without_spare_last_page(img)))


def source_label(question):
    paper = question.exam_paper
    label = f'{paper.year} {paper.get_paper_type_display()}'
    if paper.is_deferred:
        label += ' (deferred)'
    return f'{label}, Question {question.question_number}'


def _marks_text(marks):
    return f'({marks} marks)' if marks else None


class _ExamSheet(_Sheet):
    """Pages with the exam title at the top and a page number at the foot."""

    def stamp(self, header, first_numbered=0):
        """Header and "Page n of N" on every page from first_numbered on."""
        pages = list(self.doc)[first_numbered:]
        for number, page in enumerate(pages, start=1):
            page.insert_text(fitz.Point(MARGIN, MARGIN - 16), header,
                             fontname='helv', fontsize=HEADER_SIZE, color=GREY)
            footer = f'Page {number} of {len(pages)}'
            width = fitz.get_text_length(footer, fontname='helv', fontsize=FOOTER_SIZE)
            page.insert_text(fitz.Point((PAGE_WIDTH - width) / 2, PAGE_HEIGHT - 20),
                             footer, fontname='helv', fontsize=FOOTER_SIZE, color=GREY)


def _centred(page, y, text, size, bold=False):
    font = 'hebo' if bold else 'helv'
    width = fitz.get_text_length(text, fontname=font, fontsize=size)
    page.insert_text(fitz.Point((PAGE_WIDTH - width) / 2, y), text,
                     fontname=font, fontsize=size)


def _cover(sheet, exam, items):
    """Title, details, name lines, instructions and a marks grid on one page."""
    sheet.new_page()
    page = sheet.page
    y = MARGIN + 60
    _centred(page, y, exam.title, 22, bold=True)
    if exam.subtitle:
        y += 28
        _centred(page, y, exam.subtitle, 13)
    if exam.exam_date:
        y += 22
        _centred(page, y, exam.exam_date.strftime('%-d %B %Y'), 11)

    total = sum(item.marks for item in items)
    facts = []
    if exam.duration_minutes:
        hours, minutes = divmod(exam.duration_minutes, 60)
        facts.append('Time allowed: ' + (f'{hours} h {minutes} min' if hours and minutes
                                         else f'{hours} hours' if hours > 1
                                         else '1 hour' if hours
                                         else f'{minutes} minutes'))
    if total:
        facts.append(f'Total marks: {total}')
    facts.append(f'{len(items)} question' + ('' if len(items) == 1 else 's'))
    y += 34
    _centred(page, y, '     |     '.join(facts), 11, bold=True)

    # Name and class lines.
    y += 40
    for label in ('Name', 'Class'):
        page.insert_text(fitz.Point(MARGIN + 20, y), f'{label}:', fontname='hebo', fontsize=11)
        page.draw_line(fitz.Point(MARGIN + 70, y + 2), fitz.Point(PAGE_WIDTH - MARGIN - 20, y + 2),
                       color=(0, 0, 0), width=0.6)
        y += 30

    if exam.instructions.strip():
        y += 6
        page.insert_text(fitz.Point(MARGIN + 20, y), 'Instructions', fontname='hebo', fontsize=11)
        box = fitz.Rect(MARGIN + 20, y + 6, PAGE_WIDTH - MARGIN - 20, y + 120)
        lines = [line.strip() for line in exam.instructions.strip().splitlines() if line.strip()]
        page.insert_textbox(box, '\n'.join(f'-  {line}' for line in lines),
                            fontname='helv', fontsize=10.5, lineheight=1.4)
        y = box.y0 + 14 * 1.4 * min(len(lines), 8) + 10

    # Marks grid: one row per question and a total, to fill in when marking.
    # Rows shrink to fit what is left of the page, so a long exam still gets one.
    rows = len(items) + 2
    room = PAGE_HEIGHT - MARGIN - 30 - (y + 20)
    row_h = max(11, min(20, room / rows))
    size = min(10, row_h - 4)
    col_x = [PAGE_WIDTH / 2 - 150, PAGE_WIDTH / 2 - 30, PAGE_WIDTH / 2 + 60, PAGE_WIDTH / 2 + 150]
    top = y + 20
    cells = [('Question', 'Marks', 'Awarded')] + [
        (str(n), str(item.marks or ''), '') for n, item in enumerate(items, start=1)
    ] + [('Total', str(total or ''), '')]
    for r, row in enumerate(cells):
        y0 = top + r * row_h
        for c, value in enumerate(row):
            rect = fitz.Rect(col_x[c], y0, col_x[c + 1], y0 + row_h)
            page.draw_rect(rect, color=(0, 0, 0), width=0.5)
            bold = r == 0 or r == len(cells) - 1
            font = 'hebo' if bold else 'helv'
            width = fitz.get_text_length(value, fontname=font, fontsize=size)
            page.insert_text(fitz.Point(rect.x0 + (rect.width - width) / 2, rect.y1 - (row_h - size) / 2 - 1),
                             value, fontname=font, fontsize=size)


def build_exam_pdf(exam):
    """The exam to hand out: cover, then each question on its own page(s)."""
    return _build_exam(exam)[0]


def exam_layout(exam):
    """{item id: (first page, last page)}, numbered from 1 for the cover.

    Exactly the pages the printed exam puts each question on, because it is
    the same build: page n of a student's scanned script is page n here.
    """
    return _build_exam(exam)[1]


def _build_exam(exam):
    items = list(exam.ordered_items())
    sheet = _ExamSheet()
    _cover(sheet, exam, items)
    layout = {}

    for number, item in enumerate(items, start=1):
        question = item.question
        sheet.new_page()
        first = sheet.doc.page_count
        heading = f'Question {number}'
        if item.skip_note:
            heading += f' - {item.skip_note}'
        path = _image_path(question.image)
        img = _prepare_image(path) if path else None
        if img is None:
            sheet.text(heading, size=12, right=_marks_text(item.marks))
            sheet.text('No image of this question on file.', bold=False)
            sheet.y += GAP
        else:
            sheet.labelled_image(heading, path, size=12,
                                 img=_students_copy(img),
                                 right=_marks_text(item.marks))
        layout[item.id] = (first, sheet.doc.page_count)

    sheet.stamp(exam.title, first_numbered=1)
    return sheet.doc.tobytes(), layout


def build_exam_scheme_pdf(exam):
    """The marking scheme, under the exam's own numbering, with each source named."""
    items = list(exam.ordered_items())
    sheet = _ExamSheet()
    sheet.new_page()
    sheet.text(f'{exam.title} - Marking scheme', size=16)
    if exam.subtitle:
        sheet.text(exam.subtitle, size=11, bold=False)
    sheet.y += GAP

    for number, item in enumerate(items, start=1):
        question = item.question
        sheet.ensure(LINE_HEIGHT * 3)
        sheet.text(f'Question {number}', size=12, right=_marks_text(item.marks))
        sheet.text(f'Source: {source_label(question)}', size=9, bold=False)
        omitted = item.omitted()
        if omitted:
            sheet.text('Not set: ' + ', '.join(part.label for part in omitted), size=9, bold=False)
        crops = _scheme_crops([part for part in question.parts.all() if part not in omitted])
        if not crops:
            sheet.text('No marking scheme on file for this question.', size=10, bold=False)
        for label, path in crops:
            sheet.labelled_image(label, path, size=10)
        sheet.y += GAP

    sheet.stamp(f'{exam.title} - Marking scheme')
    return sheet.doc.tobytes()
