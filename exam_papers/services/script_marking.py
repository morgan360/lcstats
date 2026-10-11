"""Marking a student's answered exam paper, one question at a time.

The student wrote on the printed paper, so a question's pages are the scan's
pages at the same numbers (``exam_pdf.exam_layout``). Each question goes to the
vision model once, with those pages and each part's marking-scheme crop and
marks, and comes back with a transcription, a mark and a line of feedback per
part.

The mark is decided in code, not taken on the model's word, by the same rule as
the work-photo marker (``work_analysis._sanitise_mark``): an unreadable page, a
low-confidence read or a number outside 0..max gives no mark at all, for the
teacher to fill in. A part with no marking scheme on file is never sent for a
mark. Nothing here is final: the teacher reviews every mark before the results
sheet is printed.

One question per request, driven from the browser, as Homework Check does: a
question with three pages of handwriting can take a minute or more, and there
is no background queue.
"""
import json
import logging
import re

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from openai import APIConnectionError

from students.services.image_intake import encode_for_api

from ..models import ExamScriptMark, ExamScriptQuestion
from .vision_grading import _vision_completion, as_image_list, encode_image_from_file, vision_model
from .work_analysis import _parse_json_response, _sanitise_mark

logger = logging.getLogger(__name__)

# A whole question: a transcription and a mark for each of up to four parts.
MAX_TOKENS = 6000

# A full A4 page of handwriting needs more than the 1024px a single work photo
# gets: at that size a page of small writing is about 7px a line.
PAGE_MAX_EDGE = int(getattr(settings, 'EXAM_SCRIPT_API_MAX_EDGE', 1600))

STALLED_MESSAGE = ("The marker took too long to answer for this question. Nothing was lost: "
                   "press Mark again to retry it.")
FAILED_MESSAGE = "This question couldn't be marked automatically. Enter its marks yourself."
NO_SCHEME_NOTE = "No marking scheme on file for this part: enter the mark yourself."


class Stalled(Exception):
    """Timed out or the connection dropped: retryable, nothing is wrong with the pages."""


def mark_rows(item):
    """What gets a mark on this question: [(part or None, label, max marks, scheme images)].

    One row per part still set when every part carries its own marks. When the
    parts' marks were never filled in, only the question's total is known, so
    the question is marked as one row.
    """
    omitted = {part.id for part in item.omitted_parts.all()}
    # By label, not the stored order: some questions' parts were entered out of
    # order ((a), (c), (b)), and LC part letters always run alphabetically.
    parts = sorted((part for part in item.question.parts.all() if part.id not in omitted),
                   key=lambda part: part.label)
    if parts and all(part.max_marks for part in parts):
        return [(part, part.label, part.max_marks, as_image_list(part.solution_images))
                for part in parts]
    schemes = [image for part in parts for image in as_image_list(part.solution_images)]
    return [(None, 'Whole question', item.marks, schemes)]


def ensure_mark_rows(script_question):
    """Create the question's marks rows if it has none yet."""
    if script_question.marks.exists():
        return
    rows = [ExamScriptMark(question=script_question, part=part, label=label,
                           max_marks=max_marks or 0, order=order,
                           feedback='' if schemes else NO_SCHEME_NOTE)
            for order, (part, label, max_marks, schemes) in enumerate(mark_rows(script_question.item))]
    ExamScriptMark.objects.bulk_create(rows)


def _prompt(number, rows, skip_note):
    lines = [
        "You are an experienced Leaving Certificate Higher Level Maths examiner, marking a "
        "student's answers to one question of a school exam against the official SEC marking "
        "scheme.",
        "",
        f"The photographs are the student's answer pages for **Question {number}**. The question "
        "is printed on the page and the student wrote their answers in the spaces under each "
        "part. Ignore anything printed; mark only what the student wrote.",
    ]
    if skip_note:
        lines += ["", f"Students were told: \"{skip_note}\" Ignore anything written for "
                      "that part; it is not marked."]
    lines += ["", "**Mark these parts, using the marking scheme image given for each:**"]
    for _, label, max_marks, _schemes in rows:
        lines.append(f"- {label}: {max_marks} marks")
    lines += [
        "",
        "For each part, in order:",
        "1. Transcribe what the student wrote for that part, line by line, exactly as written. "
        "Do not correct anything while transcribing.",
        "2. Apply the marking scheme exactly as an SEC examiner would: its scale, its partial "
        "credit levels, what full credit requires. Credit a correct method with a slip as the "
        "scheme says, not as fully wrong.",
        "3. Give the mark as a whole number between 0 and the part's maximum.",
        "4. One or two sentences of feedback addressed to the student: what earned the marks and "
        "what lost them.",
        "",
        "If a part has no attempt at all, set has_working to false and the mark to 0. If you "
        "cannot read the handwriting well enough to be sure of a mark, set readable to false or "
        "confidence to low, and the teacher will mark it.",
        "",
        "Reply with JSON only, in this shape:",
        '{"parts": [{"label": "(a)", "readable": true, "has_working": true, '
        '"confidence": "high|medium|low", "transcription": "...", "estimated_mark": 7, '
        '"mark_reasoning": "which scale point and why", "feedback": "..."}]}',
        "Use the labels exactly as listed above. Write maths in LaTeX between $ signs.",
    ]
    return "\n".join(lines)


# The model sometimes opens inline maths with $$ and closes it with $, as in
# "$$\\sqrt{-7}$", which KaTeX then renders as a runaway display block.
_LOPSIDED_MATHS = re.compile(r'(?<!\$)\$\$([^$]+?)\$(?!\$)')


def tidy_maths(text):
    return _LOPSIDED_MATHS.sub(r'$\1$', str(text or ''))


def _settle_mark(result, max_marks):
    """The mark to record for one part, or None for the teacher to give.

    A blank answer, clearly read, is worth 0, which is not the same as an
    unreadable one. Everything else goes through the work-photo marker's rule.
    """
    readable = result.get('readable', True)
    confident = (result.get('confidence') or '').lower() != 'low'
    if result.get('has_working') is False and readable and confident:
        return 0
    _sanitise_mark(result, max_marks)
    return result.get('estimated_mark')


def mark_question(script_question):
    """Mark one question of one script. Raises Stalled for a retryable timeout."""
    ensure_mark_rows(script_question)
    item = script_question.item
    rows = mark_rows(item)
    marks = {mark.label: mark for mark in script_question.marks.all()}
    to_mark = [row for row in rows if row[3] and row[2]]

    pages = list(script_question.script.pages.filter(number__in=script_question.page_numbers()))
    if not pages:
        _finish(script_question, ExamScriptQuestion.FAILED,
                "No pages are set for this question. Set its pages, then mark again.")
        return
    if not to_mark:
        # Nothing on file to mark against: leave every part for the teacher.
        _finish(script_question, ExamScriptQuestion.MARKED, "")
        return

    number = list(item.exam.ordered_items()).index(item) + 1
    content = [{"type": "text", "text": _prompt(number, to_mark, item.skip_note)}]
    for page in pages:
        content += [
            {"type": "text", "text": f"**Answer page {page.number}:**"},
            {"type": "image_url", "image_url": {
                "url": f"data:image/jpeg;base64,{encode_for_api(page.image, PAGE_MAX_EDGE)}",
                "detail": "high"}},
        ]
    for _, label, max_marks, schemes in to_mark:
        for index, scheme in enumerate(schemes):
            b64 = encode_image_from_file(scheme)
            if not b64:
                continue
            heading = f"**Marking scheme for {label} ({max_marks} marks)"
            content += [
                {"type": "text", "text": heading + (":**" if not index else ", continued:**")},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}",
                                                    "detail": "high"}},
            ]

    try:
        response = _vision_completion(
            messages=[{"role": "user", "content": content}],
            max_tokens=MAX_TOKENS, temperature=0.1,
            response_format={"type": "json_object"},
        )
    except APIConnectionError as e:  # APITimeoutError is a subclass
        logger.warning("Exam script question %s did not come back (%s)",
                       script_question.pk, type(e).__name__)
        raise Stalled(STALLED_MESSAGE) from e

    raw = (response.choices[0].message.content or '').strip()
    try:
        parsed = _parse_json_response(raw) if raw else {}
    except (ValueError, json.JSONDecodeError):
        parsed = {}
    if not isinstance(parsed, dict):
        parsed = {}
    results = {str(part.get('label', '')).strip(): part for part in parsed.get('parts', [])
               if isinstance(part, dict)}
    if not results:
        logger.warning("Exam script question %s: no usable reply (%r)", script_question.pk, raw[:200])
        _finish(script_question, ExamScriptQuestion.FAILED, FAILED_MESSAGE)
        return

    usage = getattr(response, 'usage', None)
    with transaction.atomic():
        for _, label, max_marks, _schemes in to_mark:
            mark = marks.get(label)
            result = results.get(label) or results.get(label.strip('()'))
            if mark is None:
                continue
            if result is None:
                mark.ai_mark = None
                mark.feedback = "The marker gave no mark for this part: enter it yourself."
            else:
                mark.ai_mark = _settle_mark(result, max_marks)
                mark.transcription = tidy_maths(result.get('transcription'))[:4000]
                mark.reasoning = tidy_maths(result.get('mark_reasoning'))[:2000]
                mark.feedback = tidy_maths(result.get('feedback'))[:2000]
                mark.confidence = str(result.get('confidence') or '')[:8]
            mark.save()
        script_question.model_used = vision_model()
        script_question.prompt_tokens = getattr(usage, 'prompt_tokens', 0) or 0
        script_question.completion_tokens = getattr(usage, 'completion_tokens', 0) or 0
        _finish(script_question, ExamScriptQuestion.MARKED, "")


def _finish(script_question, status, message):
    script_question.status = status
    script_question.message = message[:300]
    script_question.marked_at = timezone.now()
    script_question.save()


def next_pending(script):
    return script.questions.filter(status=ExamScriptQuestion.PENDING).select_related(
        'item__question', 'item__exam', 'script').first()
