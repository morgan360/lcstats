"""Finding the exercises inside a solutions PDF.

A chapter of worked solutions runs to 80-odd pages, and sending all of them to
the vision model with every batch of photos is both ruinously slow and the kind
of bill nobody wants to explain. Almost all of that PDF is irrelevant to any one
piece of homework: what matters is the four or five pages covering the exercise
that was actually set.

So the pages are indexed once, by reading the running header that these books
print on every page ("Exercise 1.3"), and a teacher picks the exercise by name
rather than working out a page range by hand.

This reads the PDF's **text layer**, which is a different proposition from the
exam-question extraction that was abandoned as unreliable. That tried to
reconstruct question content and structure; this only looks for a heading that
repeats on every page, and when it finds nothing the feature degrades to the
free-text page range it replaces.
"""
import logging
import re

logger = logging.getLogger(__name__)

# "Exercise 1.3", "EXERCISE 12.4", "Exercise 7" -- the running header these
# solution books carry on every page of an exercise.
#
# Anchored to the start of a line, because the header IS a line. Searching the
# page as one string let a match run through the line break and pick up the
# chapter number printed beneath: the header "Revision Exercise" followed by
# "07" was read as "Exercise 07", which named a section that does not exist and
# handed the teacher fourteen wrong pages.
NUMBERED_RE = re.compile(r"^Exercise\s+(\d+(?:\.\d+)?)\b", re.IGNORECASE)

# The back of a chapter carries sections that are named rather than numbered --
# "Revision Exercise", "Exam Questions", "Exam-style Questions" -- and those are
# exactly what gets set for homework, so they have to be pickable too. The whole
# line must be the heading, and short, which is what keeps this off body text.
NAMED_RE = re.compile(r"^(?:[A-Za-z][\w'-]*[ -])+(?:Exercises?|Questions)$",
                      re.IGNORECASE)
MAX_NAMED_LENGTH = 40

# A run shorter than this is usually a cross-reference in the body text
# ("see Exercise 1.4"), not the exercise actually starting on that page.
MIN_RUN_PAGES = 1


def _line_label(line):
    """The section heading this line is, or None."""
    numbered = NUMBERED_RE.match(line)
    if numbered:
        return f"Exercise {numbered.group(1)}"
    if len(line) <= MAX_NAMED_LENGTH and NAMED_RE.match(line):
        return line
    return None


def _page_label(page):
    """The section this page belongs to, or None.

    Takes the *first* heading line on the page: the running header sits above
    the body, so a mention of another exercise further down does not win.
    """
    for raw in (page.get_text() or "").split("\n"):
        label = _line_label(raw.strip())
        if label:
            return label
    return None


def detect_sections(pdf_path):
    """Find each exercise and the page range it covers.

    Returns a list of {'label', 'first_page', 'last_page'} in page order.
    Empty when the PDF carries no such headings, which is the signal to fall
    back to a hand-typed page range.
    """
    import fitz

    doc = fitz.open(pdf_path)
    try:
        labels = [_page_label(doc[i]) for i in range(len(doc))]
    finally:
        doc.close()

    sections = []
    current = None
    start = None

    for index, label in enumerate(labels):
        page_number = index + 1
        if label != current:
            if current is not None:
                sections.append((current, start, page_number - 1))
            current, start = label, page_number
    if current is not None:
        sections.append((current, start, len(labels)))

    out = []
    for label, first, last in sections:
        if label is None:
            continue
        if last - first + 1 < MIN_RUN_PAGES:
            continue
        out.append({
            "label": label,
            "first_page": first,
            "last_page": last,
        })

    logger.info("Detected %s exercise section(s) in %s", len(out), pdf_path)
    return out


def build_sections(solution, force=False):
    """Index a solution's exercises, caching them as rows.

    Idempotent: does nothing if the solution has already been indexed, unless
    ``force``. Returns the section rows in page order.
    """
    from .models import HWSolutionSection

    existing = list(solution.sections.order_by("first_page"))
    if existing and not force:
        return existing
    if force:
        solution.sections.all().delete()

    if not solution.pdf_file:
        return []

    rows = [
        HWSolutionSection(
            solution=solution,
            label=s["label"][:100],
            first_page=s["first_page"],
            last_page=s["last_page"],
        )
        for s in _longest_run_per_label(detect_sections(solution.pdf_file.path))
    ]
    HWSolutionSection.objects.bulk_create(rows)
    return list(solution.sections.order_by("first_page"))


def _longest_run_per_label(sections):
    """One row per exercise, keeping the run that actually holds its solutions.

    ``detect_sections`` stays honest about the page order and will report an
    exercise twice if its header reappears after a gap -- a revision page, a
    reprise at the end of a chapter. Two rows with the same label would break
    the (solution, label) uniqueness, and picking the one-page reprise over the
    real five-page run would send the model the wrong pages, so the longest run
    wins.
    """
    best = {}
    for section in sections:
        label = section["label"]
        length = section["last_page"] - section["first_page"]
        if label not in best or length > (best[label]["last_page"]
                                          - best[label]["first_page"]):
            best[label] = section
    return sorted(best.values(), key=lambda s: s["first_page"])
