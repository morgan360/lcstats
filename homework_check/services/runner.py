"""Driving one check through its chunks, one call per request.

The browser is the queue runner: the detail page POSTs to analyse-next
repeatedly until the check is complete. That is what keeps a sixteen-photo
exercise inside OPENAI_VISION_TIMEOUT without introducing Celery, and it makes
the work resumable -- closing the tab pauses it, reopening the check carries on
from the first photo not yet analysed.
"""
import logging

from django.conf import settings
from django.utils import timezone

from students.services.image_intake import encode_for_api, encode_path_for_api

from . import assembly
from .check_analysis import analyse_chunk
from .solution_pages import pages_for_check
from .summarise import summarise

logger = logging.getLogger(__name__)

# Shown to a teacher when a chunk fails for any reason. One fixed string: the
# exception text stays in the log, where it is useful, and out of the page,
# where it is noise at best and a leak at worst.
ANALYSIS_FAILED_MESSAGE = (
    "That batch couldn't be read. Check the photos are flat, straight on and "
    "in good light, then try again."
)


class TooManySolutionPages(Exception):
    """The chosen page range is too big to send with every batch.

    Its message is written to be read by a teacher: it names the number and
    says what to do, because the fix is theirs to make, not a fault to log.
    """


def _encode_solution_pages(check):
    """Base64 the scoped solution pages, with their page numbers.

    Guarded on count: these images are re-sent with every batch of photos, so
    a whole chapter here is multiplied by the number of batches.
    """
    pages = pages_for_check(check.solution, check.solution_pages)

    limit = getattr(settings, "HOMEWORK_CHECK_MAX_SOLUTION_PAGES", 12)
    if len(pages) > limit:
        raise TooManySolutionPages(
            f"That's {len(pages)} pages of solutions to check against, and the "
            f"limit is {limit}. Pick the exercise this homework came from, or "
            f"type a narrower page range, then try again."
        )

    encoded = []
    numbers = []
    for page in pages:
        with page.image.open("rb") as fh:
            encoded.append(encode_path_for_api(fh))
        numbers.append(page.page_number)
    return encoded, numbers


def analyse_next_chunk(check):
    """Analyse the next batch of pending photos. Returns (done, total).

    Raises on failure. The caller decides what the teacher sees, so that no
    exception text can reach a page.
    """
    from ..models import CheckPhoto, HomeworkCheck

    batch = list(check.pending_photos()[:check.chunk_size])
    if not batch:
        return check.progress()

    if check.status != HomeworkCheck.Status.ANALYSING:
        check.status = HomeworkCheck.Status.ANALYSING
        check.save(update_fields=["status"])

    page_b64s, page_numbers = _encode_solution_pages(check)
    photo_b64s = [encode_for_api(p.image) for p in batch]

    first = batch[0].order + 1
    label = f"photos {first}-{first + len(batch) - 1}"

    try:
        result = analyse_chunk(
            photo_b64s, page_b64s, check.exercise_name,
            page_numbers=page_numbers, chunk_label=label,
        )
    except Exception:
        CheckPhoto.objects.filter(pk__in=[p.pk for p in batch]).update(
            status=CheckPhoto.Status.FAILED
        )
        raise

    check.analysis = list(check.analysis or []) + [result]
    check.prompt_tokens += result["usage"]["prompt_tokens"]
    check.completion_tokens += result["usage"]["completion_tokens"]
    check.model_used = result.get("model_used", "")[:64]
    check.save(update_fields=[
        "analysis", "prompt_tokens", "completion_tokens", "model_used",
    ])

    CheckPhoto.objects.filter(pk__in=[p.pk for p in batch]).update(
        status=CheckPhoto.Status.ANALYSED
    )

    return check.progress()


def finalise(check):
    """Assemble the report once every photo has been through a chunk."""
    from ..models import HomeworkCheck

    chunks = list(check.analysis or [])
    report = assembly.assemble(chunks)

    check.findings = report["questions"]
    check.counts = report["counts"]
    check.rating = report["rating"]
    check.rating_reason = report["rating_reason"][:200]
    check.has_diagram = report["has_diagram"]
    check.diagram_feedback = report["diagram_feedback"]
    check.readable = report["readable"]
    check.confidence = report["confidence"][:8]
    check.notes = report["notes"]

    if report["questions"]:
        try:
            text, usage = summarise(check.exercise_name, report["questions"])
            check.summary = text
            check.prompt_tokens += usage["prompt_tokens"]
            check.completion_tokens += usage["completion_tokens"]
        except Exception:
            # The report is worth printing without its closing note, so this
            # is logged and stepped over rather than failing the whole check.
            logger.exception("Summary call failed for check %s", check.pk)
            check.summary = assembly.fallback_summary(
                report["questions"], report["counts"])
    else:
        check.summary = assembly.fallback_summary(
            report["questions"], report["counts"])

    check.status = HomeworkCheck.Status.COMPLETE
    check.analysed_at = timezone.now()
    check.save()

    logger.info(
        "Completed homework check %s: %s question(s), rating=%s tokens=%s/%s",
        check.pk, len(report["questions"]), check.rating or "withheld",
        check.prompt_tokens, check.completion_tokens,
    )
    return report
