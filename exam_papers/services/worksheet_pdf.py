"""Turn a chosen set of exam questions into a PDF worksheet.

The printable page already exists; this is for when a teacher wants a file to
keep or send rather than whatever the browser's print dialogue produces. The
images are the same ones the page shows - the question crop from the paper, and
each part's marking scheme row.
"""
import io
import os

import fitz
from PIL import Image

PAGE_WIDTH, PAGE_HEIGHT = fitz.paper_size('a4')
MARGIN = 40
HEADING_SIZE = 11
LINE_HEIGHT = 16
GAP = 14

# A question crop is a whole exam page, so it rarely fits under whatever is
# already on the page. Rather than leave the rest of a page empty, an image is
# shrunk to the space left when that space is still most of a page.
SQUEEZE_RATIO = 0.6

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
    """(jpeg bytes, width, height) for one image, or None if it cannot be read."""
    try:
        with Image.open(path) as img:
            img = img.convert('RGB')
            if img.width > MAX_IMAGE_WIDTH_PX:
                height = round(img.height * MAX_IMAGE_WIDTH_PX / img.width)
                img = img.resize((MAX_IMAGE_WIDTH_PX, height), Image.LANCZOS)
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=JPEG_QUALITY, optimize=True)
            return buffer.getvalue(), img.width, img.height
    except (OSError, ValueError):
        return None


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
        prepared = _prepare_image(path)
        if not prepared:
            self.text(label, size=size)
            self.text('No usable image on file.', size=size, bold=False)
            self.y += GAP
            return

        data, width, height = prepared
        full_page = PAGE_HEIGHT - 2 * MARGIN - LINE_HEIGHT
        here = (self.space_left() - LINE_HEIGHT) if self.page else 0

        # Use what is left of this page when that is still most of a page;
        # otherwise start a page and take the whole of it.
        if here >= full_page * SQUEEZE_RATIO:
            usable = here
        else:
            self.new_page()
            usable = full_page

        draw_width = self.width
        draw_height = height * (draw_width / width)
        if draw_height > usable:
            draw_height = usable
            draw_width = width * (draw_height / height)

        self.ensure(LINE_HEIGHT + draw_height)
        self.text(label, size=size)
        self.page.insert_image(
            fitz.Rect(MARGIN, self.y, MARGIN + draw_width, self.y + draw_height),
            stream=data,
        )
        self.y += draw_height + GAP

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


def build_parts_worksheet_pdf(groups, title=None):
    """A sheet of selected question parts, under the question they belong to.

    ``groups`` is [(question, [part, ...])], as the parts page posts them. A
    part has no image of its own, so its question's image is printed once and
    the ticked parts' marking schemes follow it -- which is the only way a
    part-level sheet says what was actually asked.
    """
    sheet = _Sheet()
    if title:
        sheet.text(title, size=HEADING_SIZE + 2)
        sheet.y += GAP

    for question, parts in groups:
        labels = ', '.join(part.label for part in parts)
        heading = (f'{question.exam_paper.year} '
                   f'{question.exam_paper.get_paper_type_display()} - '
                   f'Question {question.question_number} {labels}'.strip())

        path = _image_path(question.image)
        if path:
            sheet.labelled_image(heading, path)
        else:
            sheet.ensure(LINE_HEIGHT * 2)
            sheet.text(heading)
            sheet.text('No image of this question on file.', bold=False)
            sheet.y += GAP

        crops = _scheme_crops(parts)
        if crops:
            sheet.ensure(LINE_HEIGHT * 2)
            sheet.text('Marking scheme')
            for label, crop_path in crops:
                sheet.labelled_image(label, crop_path, size=10)

    return sheet.bytes()
