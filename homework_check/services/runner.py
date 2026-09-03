"""Driving one check through its chunks, one call per request.

The browser is the queue runner: the detail page POSTs to analyse-next
repeatedly until the check is complete. That is what keeps a sixteen-photo
exercise inside OPENAI_VISION_TIMEOUT without introducing Celery, and it makes
the work resumable -- closing the tab pauses it, reopening the check carries on
from the first photo not yet analysed.
"""
import hashlib
import logging

from django.conf import settings
from django.utils import timezone
from openai import APIConnectionError

from students.services.image_intake import encode_for_api, encode_path_for_api

from . import assembly
from .check_analysis import EmptyResponse, analyse_chunk
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


# Same shape as ANALYSIS_FAILED_MESSAGE, but this one is not the photos'
# fault and the batch is still there to retry, so it says so.
ANALYSIS_STALLED_MESSAGE = (
    "That batch took too long to come back. Nothing is wrong with the photos "
    "and none of them have been used up -- press the button again to carry "
    "on. If it keeps happening, the pages are quicker in smaller batches."
)


class Stalled(Exception):
    """The model call timed out or the connection dropped.

    Retryable, and it says nothing about the photographs, so it is kept apart
    from a genuine failure. Its message is written to be read by a teacher.
    """


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

    limit = getattr(settings, "HOMEWORK_CHECK_MAX_SOLUTION_PAGES", 30)
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


def _cache_key(check):
    """Group requests that begin with the same prefix.

    Keyed on everything that prefix actually contains -- the exercise name,
    which is in the prompt, then the solutions and the page range -- and
    deliberately not on the check or the student. Marking a class is
    twenty-five checks that all open with the same eleven solution pages, and
    they should all reuse the cache the first one warmed.

    The name is hashed rather than written in because it is free text and the
    key has to stay short and printable. A collision costs nothing: the key
    only decides which cache a request is routed to, and an exact prefix
    match is still what earns the discount.
    """
    name = hashlib.md5(check.exercise_name.encode("utf-8")).hexdigest()[:8]
    return f"hwcheck-{check.solution_id}-{check.solution_pages or 'all'}-{name}"


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
            cache_key=_cache_key(check),
        )
    except EmptyResponse:
        # Retryable, and nothing is wrong with these photos, so they stay
        # pending. Marking them failed would drop them from pending_photos()
        # and count them as done in progress(), which is how a check reached
        # "8/8 complete" with four of its pages never looked at.
        raise
    except APIConnectionError as e:
        # A timeout or a dropped connection, which is exactly the same
        # situation: the photos were never read, so they must stay pending
        # for the same reason. Marking them failed here is how check 13 came
        # to sit at "8/8" with its last four pages never looked at -- the
        # batch had timed out, not been rejected. APITimeoutError is a
        # subclass of this, so both arrive here.
        logger.warning(
            "Homework check %s: batch of %s did not come back (%s)",
            check.pk, len(batch), type(e).__name__,
        )
        raise Stalled(ANALYSIS_STALLED_MESSAGE) from e
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

    from ..models import CheckPhoto

    chunks = list(check.analysis or [])
    failed_photos = check.photos.filter(status=CheckPhoto.Status.FAILED).count()
    report = assembly.assemble(chunks, failed_photos=failed_photos)

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
