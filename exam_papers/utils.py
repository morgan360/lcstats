# exam_papers/utils.py
"""
Utilities for processing exam paper PDFs and extracting question images.
"""
import fitz  # PyMuPDF
from PIL import Image
import io
import os
import re
from django.core.files.base import ContentFile


def extract_pdf_pages_as_images(pdf_path, output_dir=None, dpi=200):
    """
    Extract each page of a PDF as a high-quality image.

    Args:
        pdf_path: Path to the PDF file
        output_dir: Directory to save images (optional)
        dpi: Resolution for image extraction (default 200)

    Returns:
        List of tuples (page_number, image_bytes)
    """
    doc = fitz.open(pdf_path)
    images = []

    # Calculate zoom for desired DPI (72 is default PDF DPI)
    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)

    for page_num in range(len(doc)):
        page = doc[page_num]
        pix = page.get_pixmap(matrix=mat)

        # Convert to PIL Image
        img_data = pix.tobytes("png")

        # Optionally save to file
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            filename = f"page_{page_num + 1}.png"
            filepath = os.path.join(output_dir, filename)
            pix.save(filepath)

        images.append((page_num + 1, img_data))

    doc.close()
    return images


def split_pdf_into_questions(pdf_path, num_questions, output_dir=None):
    """
    Split a PDF into individual question images.
    Assumes questions are distributed evenly across pages.

    Args:
        pdf_path: Path to the PDF file
        num_questions: Number of questions in the paper
        output_dir: Directory to save question images (optional)

    Returns:
        List of tuples (question_number, image_bytes)
    """
    # First, extract all pages
    pages = extract_pdf_pages_as_images(pdf_path)

    # Calculate pages per question (rough approximation)
    total_pages = len(pages)
    pages_per_question = total_pages / num_questions

    question_images = []

    for q_num in range(1, num_questions + 1):
        # Determine which page(s) this question is likely on
        start_page = int((q_num - 1) * pages_per_question)
        end_page = int(q_num * pages_per_question)

        # For now, just take the first page of each question
        # (Can be enhanced to combine multiple pages)
        if start_page < len(pages):
            page_num, img_data = pages[start_page]

            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
                filename = f"question_{q_num}.png"
                filepath = os.path.join(output_dir, filename)
                with open(filepath, 'wb') as f:
                    f.write(img_data)

            question_images.append((q_num, img_data))

    return question_images


def extract_pdf_page_ranges(pdf_path, page_ranges, output_dir=None):
    """
    Extract specific page ranges from PDF as images.
    More precise than automatic splitting.

    Args:
        pdf_path: Path to the PDF file
        page_ranges: List of tuples (question_num, start_page, end_page)
                    Example: [(1, 1, 1), (2, 2, 3), (3, 4, 4)]
        output_dir: Directory to save images (optional)

    Returns:
        List of tuples (question_number, image_bytes)
    """
    doc = fitz.open(pdf_path)
    question_images = []

    dpi = 200
    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)

    for question_num, start_page, end_page in page_ranges:
        # If single page, just extract that page
        if start_page == end_page:
            page = doc[start_page - 1]  # 0-indexed
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")

            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
                filename = f"question_{question_num}.png"
                filepath = os.path.join(output_dir, filename)
                with open(filepath, 'wb') as f:
                    f.write(img_data)

            question_images.append((question_num, img_data))
        else:
            # Multiple pages - combine them vertically
            images_to_combine = []
            for page_num in range(start_page - 1, end_page):
                page = doc[page_num]
                pix = page.get_pixmap(matrix=mat)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                images_to_combine.append(img)

            # Combine images vertically
            total_width = images_to_combine[0].width
            total_height = sum(img.height for img in images_to_combine)

            combined = Image.new('RGB', (total_width, total_height))
            y_offset = 0
            for img in images_to_combine:
                combined.paste(img, (0, y_offset))
                y_offset += img.height

            # Save combined image
            img_buffer = io.BytesIO()
            combined.save(img_buffer, format='PNG')
            img_data = img_buffer.getvalue()

            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
                filename = f"question_{question_num}.png"
                filepath = os.path.join(output_dir, filename)
                with open(filepath, 'wb') as f:
                    f.write(img_data)

            question_images.append((question_num, img_data))

    doc.close()
    return question_images


def get_pdf_info(pdf_path):
    """
    Get basic information about a PDF file.

    Returns:
        dict with page_count, dimensions, etc.
    """
    doc = fitz.open(pdf_path)
    info = {
        'page_count': len(doc),
        'metadata': doc.metadata,
        'pages': []
    }

    for page_num in range(len(doc)):
        page = doc[page_num]
        info['pages'].append({
            'number': page_num + 1,
            'width': page.rect.width,
            'height': page.rect.height
        })

    doc.close()
    return info


# Structure detection --------------------------------------------------------
#
# LC papers carry a real text layer, so the page each question starts on, its
# mark value and its part labels can be read straight out of the PDF instead of
# being worked out by eye and passed as --page-ranges.
#
# The maths itself does NOT come out reliably (radical extents are lost, math
# italics are doubled, fractions collapse into separate lines), so this reads
# structure only - the question images stay the source of truth for wording.

_Q_HEADER = re.compile(r"^\s*Question\s+(\d+)\s*$", re.M)
# Papers before 2012 Paper 2 number questions "1." on a line of their own, and
# fit two to a page - so they are located by position, not by page.
_LEGACY_Q = re.compile(r"^(\d{1,2})\.$")
_LEGACY_PART = re.compile(r"^\(([a-h])\)$")
_MARKS_EACH = re.compile(r"\((\d+)\s*marks?\s+each\)", re.I)
_MARKS = re.compile(r"\((\d+)\s*marks?\)", re.I)
# A part label starts a line, but the wording may follow on the same line or on
# the next one - both happen within a single paper. Restricting to a-h excludes
# the roman sub-parts (i), (v), (x) for free; LC parts have never reached (g).
_PART = re.compile(r"^\s*\(([a-h])\)(?=\s|$)", re.M)
_BLANK_HINT = re.compile(r"do not write on this page", re.I)


def detect_question_layout(pdf_path):
    """Read question structure from an exam paper's text layer.

    Returns a list of dicts, ordered by page:

        [{"question": 1, "start_page": 4, "end_page": 5,
          "marks": 30, "parts": ["a", "b", "c"]}, ...]

    Pages are 1-indexed, matching extract_pdf_page_ranges(). Returns [] for
    papers that do not use the "Question N" heading - papers before 2012 Paper 2
    use a different layout and still need --page-ranges by hand.
    """
    doc = fitz.open(pdf_path)
    try:
        pages = [doc[i].get_text() for i in range(doc.page_count)]
        page_count = doc.page_count
    finally:
        doc.close()

    # First sighting of each question number, in page order
    seen, ordered = set(), []
    for i, text in enumerate(pages):
        for match in _Q_HEADER.finditer(text):
            num = int(match.group(1))
            if num not in seen:
                seen.add(num)
                ordered.append((num, i))

    layout = []
    for idx, (num, start) in enumerate(ordered):
        end = ordered[idx + 1][1] - 1 if idx + 1 < len(ordered) else page_count - 1

        # Trim trailing blank / "do not write on this page" sheets so a question
        # does not absorb the filler pages before the next one.
        while end > start:
            tail = pages[end].strip()
            if len(tail) < 120 or _BLANK_HINT.search(tail):
                end -= 1
            else:
                break

        body = "\n".join(pages[start:end + 1])
        marks = _MARKS.search(body)
        parts = []
        for match in _PART.finditer(body):
            if match.group(1) not in parts:
                parts.append(match.group(1))

        layout.append({
            "question": num,
            "start_page": start + 1,
            "end_page": end + 1,
            "marks": int(marks.group(1)) if marks else None,
            "parts": parts,
        })

    return layout


def _text_lines(page):
    """Yield (text, bbox) for each line of text on a page."""
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            text = "".join(span["text"] for span in line["spans"]).strip()
            if text:
                yield text, line["bbox"]


def detect_legacy_question_layout(pdf_path, top_padding=14, gap=8, footer_margin=56):
    """Read question structure from a pre-2012-Paper-2 exam paper.

    These papers fit two questions to a page and number them "1." rather than
    "Question 1", so a question is a *region* of a page, not a page range:

        [{"question": 1, "start_page": 2, "end_page": 2,
          "clip": (0, 43, 595, 378), "marks": 50, "parts": ["a", "b", "c"]}, ...]

    The clip is a rectangle in PDF points, running from just above the question
    number down to just above the next one - or to the foot of the text on the
    last question of a page. Pass the result to extract_pdf_regions().

    Marks come from the front page, which on these papers gives one figure for
    every question ("Attempt SIX QUESTIONS (50 marks each)") rather than
    printing a value per question.
    """
    doc = fitz.open(pdf_path)
    try:
        marks_each = _MARKS_EACH.search(doc[0].get_text()) if doc.page_count else None
        marks = int(marks_each.group(1)) if marks_each else None

        layout = []
        for page_index in range(doc.page_count):
            page = doc[page_index]
            lines = list(_text_lines(page))

            headings = []
            for text, bbox in lines:
                match = _LEGACY_Q.match(text)
                if match:
                    headings.append((int(match.group(1)), bbox[1]))
            headings.sort(key=lambda h: h[1])

            for i, (num, top) in enumerate(headings):
                bottom = (
                    headings[i + 1][1] - gap if i + 1 < len(headings)
                    else page.rect.height - footer_margin
                )
                y0 = max(0, top - top_padding)

                parts = []
                for text, bbox in lines:
                    part = _LEGACY_PART.match(text)
                    if part and y0 <= bbox[1] < bottom and part.group(1) not in parts:
                        parts.append(part.group(1))
                parts.sort()

                layout.append({
                    "question": num,
                    "start_page": page_index + 1,
                    "end_page": page_index + 1,
                    "clip": (0, y0, page.rect.width, bottom),
                    "marks": marks,
                    "parts": parts,
                })
    finally:
        doc.close()

    layout.sort(key=lambda item: item["question"])
    return layout


# Marking scheme layout ------------------------------------------------------
#
# A scheme covers both papers in one PDF, laid out as a table per question: a
# "Q<n>" header, then a row per part carrying the model solution and the marking
# notes. Labels sit in a narrow left-hand column, so a part is the slice of page
# between its own label and the next one.

_MS_PAPER_BREAK = re.compile(r"Marking Scheme\s*[-–]\s*Paper\s*(\d)", re.I)
_MS_QUESTION = re.compile(r"^Q\s*(\d{1,2})$")
_MS_PART = re.compile(r"^\(?([a-h])\)$")
_MS_SUBPART = re.compile(r"^\(?(i{1,3}|iv|v|vi{1,3})\)$")
_LABEL_COLUMN_X = 110
_CONTINUATION_TOP = 52


def _marking_scheme_markers(doc, first_page, last_page):
    """Collect question and part labels, in reading order, with their positions."""
    markers = []
    for page_index in range(first_page, last_page + 1):
        page = doc[page_index]
        found = []
        for text, bbox in _text_lines(page):
            if bbox[0] > _LABEL_COLUMN_X:
                continue
            question = _MS_QUESTION.match(text)
            part = _MS_PART.match(text)
            sub = _MS_SUBPART.match(text)
            if question:
                found.append((bbox[1], 'question', int(question.group(1))))
            elif part:
                found.append((bbox[1], 'part', part.group(1)))
            elif sub:
                found.append((bbox[1], 'subpart', sub.group(1).lower()))
        for y, kind, value in sorted(found):
            markers.append({'page': page_index, 'y': y, 'kind': kind, 'value': value})
    return markers


def detect_marking_scheme_layout(pdf_path, paper_number, top_padding=12,
                                 footer_margin=40):
    """Locate each question part's region within a marking scheme PDF.

    Returns a dict keyed by (question, part_letter, subpart_or_None):

        {(1, 'a', None): {"slices": [(page_index, y0, y1), ...]}, ...}

    A region runs from a label down to the next label of the same or higher
    level, and may continue across a page break - hence a list of slices rather
    than one rectangle. Both a letter and each of its roman sub-parts get an
    entry, so a caller can match whichever granularity the database uses.
    """
    doc = fitz.open(pdf_path)
    try:
        # The scheme holds both papers; find where the wanted one starts and ends.
        starts = {}
        for i in range(doc.page_count):
            match = _MS_PAPER_BREAK.search(doc[i].get_text())
            if match:
                starts.setdefault(int(match.group(1)), i)
        if paper_number not in starts:
            return {}

        first = starts[paper_number]
        later = [p for n, p in starts.items() if p > first]
        last = (min(later) - 1) if later else doc.page_count - 1

        # The page before the next paper's section is its cover sheet, and the
        # end of the PDF is usually blank. Either would be swallowed whole by
        # the final part's region, so trim back to real content first.
        while last > first and len(doc[last].get_text().strip()) < 250:
            last -= 1

        markers = _marking_scheme_markers(doc, first, last)
        if not markers:
            return {}

        page_bottoms = {
            i: doc[i].rect.height - footer_margin for i in range(first, last + 1)
        }
        width = doc[first].rect.width

        rank = {'question': 0, 'part': 1, 'subpart': 2}
        regions = {}
        question = None
        letter = None

        for index, marker in enumerate(markers):
            if marker['kind'] == 'question':
                question = marker['value']
                letter = None
                continue
            if question is None:
                continue
            if marker['kind'] == 'part':
                letter = marker['value']
                key = (question, letter, None)
            else:
                if letter is None:
                    continue
                key = (question, letter, marker['value'])

            # Run to the next marker at the same level or higher. A letter's
            # region therefore swallows its own roman sub-parts, which is what a
            # database part labelled just "(b)" needs.
            end = None
            for following in markers[index + 1:]:
                if rank[following['kind']] <= rank[marker['kind']]:
                    end = following
                    break

            slices = []
            start_page, start_y = marker['page'], max(0, marker['y'] - top_padding)
            end_page = end['page'] if end else last
            end_y = (end['y'] - 4) if end else page_bottoms[last]

            for page_index in range(start_page, end_page + 1):
                # Continuations start below the page number rather than at the
                # very top, which also reduces the leftover strip on the page
                # where the next question begins to nothing worth keeping.
                y0 = start_y if page_index == start_page else _CONTINUATION_TOP
                y1 = end_y if page_index == end_page else page_bottoms[page_index]
                if y1 - y0 > 24:
                    slices.append((page_index, y0, y1))

            if not slices:
                continue
            # The scheme repeats a parent label before each of its sub-parts -
            # "(b)", "(i)", "(b)", "(ii)" - and again after a page break. Those
            # are continuations of one part, so extend rather than replace, or a
            # letter's region would shrink to whatever followed its last repeat.
            if key in regions:
                regions[key]['slices'].extend(slices)
            else:
                regions[key] = {'slices': slices, 'width': width}
    finally:
        doc.close()

    return regions


def render_marking_scheme_region(pdf_path, region, dpi=200):
    """Render one region from detect_marking_scheme_layout() as PNG bytes."""
    doc = fitz.open(pdf_path)
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    try:
        images = []
        for page_index, y0, y1 in region['slices']:
            page = doc[page_index]
            clip = fitz.Rect(0, y0, region['width'], y1)
            pix = page.get_pixmap(matrix=mat, clip=clip)
            images.append(Image.open(io.BytesIO(pix.tobytes("png"))))

        if len(images) == 1:
            combined = images[0]
        else:
            combined = Image.new(
                'RGB',
                (max(i.width for i in images), sum(i.height for i in images)),
                'white',
            )
            offset = 0
            for image in images:
                combined.paste(image, (0, offset))
                offset += image.height

        buffer = io.BytesIO()
        combined.convert('RGB').save(buffer, format='PNG')
        return buffer.getvalue()
    finally:
        doc.close()


_PART_LABEL_LETTER = re.compile(r'([a-h])', re.I)
_PART_LABEL_ROMAN = re.compile(r'\b(i{1,3}|iv|v|vi{1,3})\b', re.I)


def parse_part_label(label):
    """Reduce a hand-entered part label to (letter, roman or None).

    Labels have been typed in eighty different shapes - "(b), (i)", "(b),(i)",
    "b(ii)", "a)", and the unclosed "(b, (ii)" - so anything that compares them
    has to work from what they mean rather than how they were written.
    """
    if not label:
        return None
    text = label.strip().lower()

    letter = _PART_LABEL_LETTER.search(text)
    if not letter:
        return None

    # Only look for a roman numeral after the letter, so the "i" of a bare "(i)"
    # is not mistaken for the part letter itself.
    roman = _PART_LABEL_ROMAN.search(text[letter.end():])
    return letter.group(1), (roman.group(1) if roman else None)


def question_text(pdf_path, item, legacy=False):
    """Return the text layer for one question from a detected layout item.

    The maths does not survive extraction - radicals lose their extent and
    fractions collapse into separate lines - so this is no use for wording. The
    prose around it comes out cleanly enough to tell what a question is *about*,
    which is what topic classification needs.
    """
    doc = fitz.open(pdf_path)
    try:
        if legacy:
            page = doc[item["start_page"] - 1]
            return page.get_text(clip=fitz.Rect(*item["clip"]))
        return "\n".join(
            doc[i].get_text()
            for i in range(item["start_page"] - 1, item["end_page"])
        )
    finally:
        doc.close()


def extract_pdf_regions(pdf_path, regions, output_dir=None, dpi=200):
    """Render each region from detect_legacy_question_layout() as an image.

    Args:
        pdf_path: Path to the PDF file
        regions: List of dicts with "question", "start_page" and "clip"
        output_dir: Directory to save images (optional)
        dpi: Resolution for image extraction (default 200)

    Returns:
        List of tuples (question_number, image_bytes)
    """
    doc = fitz.open(pdf_path)
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    images = []

    try:
        for region in regions:
            page = doc[region["start_page"] - 1]
            pix = page.get_pixmap(matrix=mat, clip=fitz.Rect(*region["clip"]))
            img_data = pix.tobytes("png")

            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
                filename = f"question_{region['question']}.png"
                with open(os.path.join(output_dir, filename), 'wb') as f:
                    f.write(img_data)

            images.append((region["question"], img_data))
    finally:
        doc.close()

    return images