"""Turning a homework solutions PDF into page images the vision model can read.

The pages are rendered once per ``HWSolution`` and cached as rows, because a
class of 25 students checked against the same sheet would otherwise re-render
the same PDF 25 times.

Deliberately images, not text. Pulling the text layer out of a maths PDF was
tried for exam questions and abandoned as too unreliable to build on; the
solutions go to the model the same way ``ExamQuestionPart.solution_image``
already does.
"""
import logging

from django.core.files.base import ContentFile

from exam_papers.utils import extract_pdf_pages_as_images

logger = logging.getLogger(__name__)

# Enough to read handwritten-style worked solutions without making each page a
# multi-megabyte PNG. Matches the default the exam extraction uses.
RENDER_DPI = 200


def parse_page_range(spec, page_count):
    """Turn "3-4", "2", "1,3-5" or "" into a sorted list of page numbers.

    Blank means every page. Anything unparseable is ignored rather than raised
    on: a teacher typing "pages 3 to 4" should get the whole sheet checked, not
    an error page.
    """
    if not spec or not str(spec).strip():
        return list(range(1, page_count + 1))

    pages = set()
    for chunk in str(spec).replace(" ", "").split(","):
        if not chunk:
            continue
        if "-" in chunk:
            start, _, end = chunk.partition("-")
            if start.isdigit() and end.isdigit():
                pages.update(range(int(start), int(end) + 1))
        elif chunk.isdigit():
            pages.add(int(chunk))

    pages = sorted(p for p in pages if 1 <= p <= page_count)
    return pages or list(range(1, page_count + 1))


def render_solution_pages(solution, force=False):
    """Render every page of ``solution.pdf_file``, caching the result.

    Returns the solution's ``HWSolutionPage`` rows in page order. Idempotent:
    a second call does nothing unless ``force``.
    """
    from hw_solutions.models import HWSolutionPage

    existing = list(solution.pages.order_by("page_number"))
    if existing and not force:
        return existing

    if force:
        for page in existing:
            page.image.delete(save=False)
        solution.pages.all().delete()

    if not solution.pdf_file:
        return []

    rendered = extract_pdf_pages_as_images(solution.pdf_file.path, dpi=RENDER_DPI)

    pages = []
    for page_number, png_bytes in rendered:
        page = HWSolutionPage(solution=solution, page_number=page_number)
        page.image.save(
            f"{solution.pk}_p{page_number}.png",
            ContentFile(png_bytes),
            save=False,
        )
        page.save()
        pages.append(page)

    solution.page_count = len(pages)
    solution.save(update_fields=["page_count"])

    logger.info("Rendered %s page(s) of HW solution %s", len(pages), solution.pk)
    return pages


def pages_for_check(solution, page_spec):
    """The rendered pages a check should compare against, in page order."""
    pages = render_solution_pages(solution)
    wanted = set(parse_page_range(page_spec, len(pages)))
    return [p for p in pages if p.page_number in wanted]
