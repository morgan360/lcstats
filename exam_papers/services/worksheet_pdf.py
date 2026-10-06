"""Turn a chosen set of exam questions into a PDF worksheet.

The printable page already exists; this is for when a teacher wants a file to
keep or send rather than whatever the browser's print dialogue produces. The
images are the same ones the page shows - the question crop from the paper, and
each part's marking scheme row.
"""
import io
import os

import fitz
import numpy as np
from PIL import Image

PAGE_WIDTH, PAGE_HEIGHT = fitz.paper_size('a4')
MARGIN = 40
HEADING_SIZE = 11
LINE_HEIGHT = 16
GAP = 14

# A question crop is a stack of whole exam pages, three to six times taller than
# it is wide. Shrinking that onto one A4 page left a strip a quarter of the
# page wide, pinned to the left margin. Every image is drawn at the full page
# width instead, and one too tall for the page carries on overleaf, cut in a
# band of blank rows so no line of print is split. One exam page at full width
# fills one A4 page almost exactly.
#
# An image starts under whatever is already on the page only when that space
# is still most of a page; otherwise it starts a fresh one.
SQUEEZE_RATIO = 0.6

# A row counts as blank when no pixel in it is darker than INK_LEVEL, and a cut
# needs a run of at least MIN_GAP_PX such rows - the gap between two lines of
# print, not the white inside a letter. The cut is looked for in the lower
# half of the slice, so a page is never left mostly empty to reach one.
INK_LEVEL = 200
MIN_GAP_PX = 8

# The crops are 200 DPI PNGs of a whole page, which go into a PDF at about
# 25MB each if handed over untouched. Re-encoding to a JPEG no wider than a
# page needs at 150 DPI brings a worksheet down to a size that can be emailed,
# and the text stays readable in print.
MAX_IMAGE_WIDTH_PX = 1240
JPEG_QUALITY = 75


def _image_path(field):
    """The file behind an ImageField, or None if it is unset or missing.

    A media file that is on one machine and not another must cost its own
    question, not the whole download.
    """
    if not field:
        return None
    try:
        path = field.path
    except (ValueError, NotImplementedError):
        return None
    return path if os.path.exists(path) else None


def _prepare_image(path):
    """The image as RGB no wider than a page needs, or None if it cannot be read."""
    try:
        with Image.open(path) as img:
            img = img.convert('RGB')
            if img.width > MAX_IMAGE_WIDTH_PX:
                height = round(img.height * MAX_IMAGE_WIDTH_PX / img.width)
                img = img.resize((MAX_IMAGE_WIDTH_PX, height), Image.LANCZOS)
            else:
                img.load()
            return img
    except (OSError, ValueError):
        return None


def _jpeg(img):
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG', quality=JPEG_QUALITY, optimize=True)
    return buffer.getvalue()


def _cut_row(img, top, limit):
    """Where to end a slice that starts at row top and may be limit rows tall.

    The middle of the lowest blank band in the lower half of the slice, or the
    limit itself when there is none (a graph or grid that runs on).
    """
    lo, hi = top + limit // 2, top + limit
    rows = np.asarray(img.crop((0, lo, img.width, hi)).convert('L'))
    blank = rows.min(axis=1) > INK_LEVEL
    run_end = None
    for y in range(len(blank) - 1, -1, -1):
        if blank[y]:
            if run_end is None:
                run_end = y
            if run_end - y + 1 >= MIN_GAP_PX and (y == 0 or not blank[y - 1]):
                return lo + (y + run_end) // 2
        else:
            run_end = None
    return hi


class _Sheet:
    """A4 pages filled top to bottom, breaking when the next block will not fit."""

    def __init__(self):
        self.doc = fitz.open()
        self.page = None
        self.y = 0
        self.width = PAGE_WIDTH - 2 * MARGIN

    def new_page(self):
        self.page = self.doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
        self.y = MARGIN

    def space_left(self):
        return PAGE_HEIGHT - MARGIN - self.y

    def ensure(self, height):
        """Start a page if height will not fit on this one."""
        if self.page is None or (height > self.space_left() and self.y > MARGIN):
            self.new_page()

    def text(self, line, size=HEADING_SIZE, bold=True):
        self.ensure(LINE_HEIGHT)
        self.page.insert_text(
            fitz.Point(MARGIN, self.y + size),
            line,
            fontname='hebo' if bold else 'helv',
            fontsize=size,
        )
        self.y += LINE_HEIGHT

    def labelled_image(self, label, path, size=HEADING_SIZE):
        """A heading and its image, kept together on one page.

        Measuring the image before the heading is written is the whole point:
        writing first would strand a heading at the foot of a page with its
        question overleaf.
        """
        img = _prepare_image(path)
        if img is None:
            self.text(label, size=size)
            self.text('No usable image on file.', size=size, bold=False)
            self.y += GAP
            return

        scale = self.width / img.width
        full_page = PAGE_HEIGHT - 2 * MARGIN - LINE_HEIGHT
        here = (self.space_left() - LINE_HEIGHT) if self.page else 0

        # Stay on this page if the image fits, or if most of a page is left
        # to start it in; otherwise start a page and take the whole of it.
        if here < img.height * scale and here < full_page * SQUEEZE_RATIO:
            self.new_page()
        self.text(label, size=size)

        top = 0
        while top < img.height:
            limit = int(self.space_left() / scale)
            if limit < MIN_GAP_PX * 2:
                self.new_page()
                continue
            bottom = img.height if img.height - top <= limit else _cut_row(img, top, limit)
            draw_height = (bottom - top) * scale
            self.page.insert_image(
                fitz.Rect(MARGIN, self.y, MARGIN + self.width, self.y + draw_height),
                stream=_jpeg(img.crop((0, top, img.width, bottom))),
            )
            self.y += draw_height
            top = bottom
            if top < img.height:
                self.new_page()
        self.y += GAP

    def bytes(self):
        if self.page is None:
            self.new_page()
            self.page.insert_text(fitz.Point(MARGIN, MARGIN + 12),
                                  'Nothing to print.', fontname='helv', fontsize=11)
        return self.doc.tobytes()


def build_worksheet_pdf(questions, include_solutions=False, title=None):
    """PDF bytes for these questions, in the order given.

    Questions whose image file is missing are listed by name instead, so one
    absent file does not cost the rest of the worksheet.
    """
    sheet = _Sheet()
    if title:
        sheet.text(title, size=14)
        sheet.y += 4

    for question in questions:
        paper = question.exam_paper
        heading = (f'{paper.year} {paper.get_paper_type_display()} '
                   f'- Question {question.question_number}')
        if question.total_marks:
            heading += f' ({question.total_marks} marks)'

        path = _image_path(question.image)
        if path:
            sheet.labelled_image(heading, path)
        else:
            sheet.ensure(LINE_HEIGHT * 2)
            sheet.text(heading)
            sheet.text('No image of this question on file.', bold=False)
            sheet.y += GAP

        if include_solutions:
            crops = _scheme_crops(question.parts.all())
            if crops:
                sheet.ensure(LINE_HEIGHT * 2)
                sheet.text('Marking scheme')
                for label, path in crops:
                    sheet.labelled_image(label, path, size=10)

    return sheet.bytes()


def _scheme_crops(parts):
    """[(label, path)] for every marking-scheme crop these parts have.

    A part that covers what used to be (b)(i) and (b)(ii) carries a crop for
    each; the second and later ones are labelled "(cont.)" so the sheet reads
    as one scheme rather than as two parts with the same name.
    """
    crops = []
    for part in parts:
        for index, image in enumerate(part.solution_images):
            path = _image_path(image)
            if not path:
                continue
            crops.append((part.label if not index else f'{part.label} (cont.)',
                          path))
    return crops
