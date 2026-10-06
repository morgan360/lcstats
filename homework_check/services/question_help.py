"""A hint on one homework question, from a photo of the student's working.

The student-facing cousin of ``check_analysis``. Both read a photo against the
worked solutions PDF, but the audience is reversed, and so is the rule that
matters most:

- ``check_analysis`` writes for a teacher and states the correct answers, which
  is safe because a teacher reads the report before it is handed back.
- This writes straight to the student, who has the exercise sheet and may not
  have the solutions. The solution pages are here only so the model can judge
  the working. It must never state the answer or copy anything from those
  pages, the same rule as ``exam_papers.services.work_analysis``. Do not
  "fix" this to match check_analysis.py.

The request is built in the same cost-conscious order as ``analyse_chunk``:
the prompt, then the solution pages, then whatever varies. Every student
asking about the same exercise then shares the cached prefix, which is why the
question number is kept out of the prompt and sent after the pages.
"""
import logging

from django.conf import settings
from django.utils import timezone

from exam_papers.services.vision_grading import _vision_completion
from exam_papers.services.work_analysis import DIAGRAM_CHECKLIST, FORMATTING_RULES
from students.services.image_intake import encode_path_for_api

from . import pricing
from .check_analysis import (
    EmptyResponse, _image_part, _other_provider, _parse_json_response, _usage,
    vision_client, vision_model,
)
from .solution_pages import pages_for_check

logger = logging.getLogger(__name__)

# One question, not a dozen, so far smaller than check_analysis's 9000. It
# still has to leave room for the model's reasoning, which comes out of the
# same budget (see check_analysis.MAX_TOKENS).
MAX_TOKENS = 4000


class Unavailable(Exception):
    """Help can't be given for this exercise. The message is student-safe."""


def encode_section_pages(section):
    """Base64 the exercise's solution pages, with their page numbers.

    Held to the same cap as Homework Check. Every request carries these pages,
    and a chapter-sized exercise would be slow and costly for one question.
    """
    pages = pages_for_check(section.solution, section.page_range)
    limit = getattr(settings, "HOMEWORK_CHECK_MAX_SOLUTION_PAGES", 30)
    if not pages:
        raise Unavailable("Help isn't available for this exercise yet.")
    if len(pages) > limit:
        logger.warning("Homework help refused for section %s: %s pages, limit %s",
                       section.pk, len(pages), limit)
        raise Unavailable("Help isn't available for this exercise yet.")

    encoded, numbers = [], []
    for page in pages:
        with page.image.open("rb") as fh:
            encoded.append(encode_path_for_api(fh))
        numbers.append(page.page_number)
    return encoded, numbers


def build_prompt(exercise_label, page_numbers=()):
    """The instructions. Identical for every question in the exercise, so cached."""
    pages = (f" (pages {', '.join(str(n) for n in page_numbers)} of the "
             f"solutions)") if page_numbers else ""
    return "\n".join([
        "You are an experienced Leaving Certificate Higher Level Maths teacher. "
        "A student is stuck on a homework question and has photographed their "
        "own handwritten working. Speak to the student directly, as you would "
        "writing in the margin of their copy.",
        "",
        f"**The exercise:** {exercise_label}{pages}. The worked solutions to "
        "every question in it follow these instructions. **They are for you "
        "only. The student cannot see them**, and has only the printed "
        "question sheet. After the solutions you are told which question the "
        "student is asking about, then shown their photo.",
        "",
        "**Work through these stages in order.**",
        "",
        "STAGE 1 - Find the question.",
        "Find that question in the worked solutions, and use its solution to "
        "judge the student's working. If you cannot find it in these pages, "
        'set "question_found" to false and say so in "method_feedback", '
        "asking the student to check the question number. Do not comment on "
        "a different question instead.",
        "",
        "STAGE 2 - Read the page.",
        "Write down what is on the page, line by line, exactly as the student "
        "wrote it. Do NOT silently correct anything while transcribing: if they "
        "wrote $2x = 6$ then $x = 4$, transcribe both as written. This "
        "transcription is shown back to the student so they can check you read "
        "their handwriting correctly, so it must be faithful rather than tidy. "
        "If the photo also shows the printed question, do not transcribe that.",
        "",
        "STAGE 3 - Judge the method.",
        "For each step, decide whether the approach is mathematically sound "
        "*even if the arithmetic slipped*. A sign error in an otherwise correct "
        "method is a very different thing from the wrong method, and the "
        "student needs to be told which one they have done. Name the first "
        "line where it goes wrong and say what is wrong with it. A correct "
        "method that differs from the worked solution is still correct: say "
        "so, and judge it on its own terms.",
        "",
        "STAGE 4 - The diagram, if there is one.",
        DIAGRAM_CHECKLIST,
        "",
        "**Be honest about what you cannot see.** Never state anything about "
        "working you cannot actually read. If the photo is blurry, angled, cut "
        'off, or the handwriting is ambiguous, say so plainly, set "readable" '
        'to false and "confidence" to "low". Asking for a clearer photo is '
        "far better than guessing at what was written.",
        "",
        "**Never give the answer away.** This is the strictest rule here, and "
        "it overrides being helpful. Do NOT state the correct final answer, do "
        "NOT write out the corrected line or the next line of working, and do "
        "NOT quote, copy or paraphrase any step of the worked solutions. Where "
        "the student has gone wrong, say what is wrong and what to reconsider, "
        "not what to write. \"Check the sign when you expand the bracket on "
        "your third line\" is right; \"it should be $2x - 6$\" is not. The "
        "worked solutions are there so you can judge the work, never to be "
        "repeated back to the student, even in part.",
        "",
        "**If the page is blank, or shows no working for this question**, set "
        '"has_working" to false, say plainly that you cannot see any working, '
        'and make "next_step" an encouragement to make a start, with a hint '
        "about where to begin but no working.",
        "",
        "**Do not award marks or a score.** This is help, not marking.",
        "",
        FORMATTING_RULES,
        "",
        "**Return ONLY a JSON object** with these exact fields:",
        '- "question_found": boolean, false if the question is not in these '
        "solution pages",
        '- "readable": boolean, false if you could not properly read the page',
        '- "has_working": boolean, false if the page is blank or shows no '
        "working for this question",
        '- "confidence": "high", "medium" or "low"',
        '- "transcription": the working as written, newline separated',
        '- "has_diagram": boolean, true if a graph or sketch is present',
        '- "steps": array of objects, each {"step": what they did, "verdict": '
        'one of "correct"/"slip"/"wrong"/"unclear", "comment": one sentence}',
        '- "method_feedback": one or two short paragraphs of prose on the method',
        '- "diagram_feedback": prose on the graph, or "" if there is no diagram',
        '- "strengths": array of short strings, things they did well',
        '- "next_step": one concrete hint for what to look at or try next',
    ])


def analyse_question(photo_b64, section, question_label):
    """Analyse one photo of working on ``question_label`` of ``section``.

    Returns the parsed dict plus 'model_used' and 'usage'. Raises
    ``Unavailable`` with a student-safe message when the exercise can't be
    used, and anything else on failure: the caller decides what the student
    sees, so no exception text can leak into the feedback.
    """
    page_b64s, page_numbers = encode_section_pages(section)

    content = [{"type": "text", "text": build_prompt(section.label, page_numbers)}]
    content.append({"type": "text", "text": "**The worked solutions:**"})
    content += [_image_part(b64, "high") for b64 in page_b64s]
    # Everything from here on varies, so it comes after the cached prefix.
    content.append({
        "type": "text",
        "text": f"**The student is asking about question {question_label} "
                f"of {section.label}. Their working:**",
    })
    content.append(_image_part(photo_b64, "high"))

    extra = {}
    if not _other_provider():
        # OpenAI's routing hint; see analyse_chunk. Not sent to other providers.
        extra["prompt_cache_key"] = f"hwhelp-{section.pk}"

    response = _vision_completion(
        messages=[{"role": "user", "content": content}],
        max_tokens=MAX_TOKENS,
        temperature=0.2,
        response_format={"type": "json_object"},
        model=vision_model(),
        client=vision_client(),
        **extra,
    )

    raw = (response.choices[0].message.content or "").strip()
    if not raw:
        raise EmptyResponse("The model returned nothing.")

    result = _parse_json_response(raw)
    result["model_used"] = vision_model()
    result["usage"] = _usage(response)
    _record_usage(result)

    logger.info(
        "Homework help (%s): section=%s question=%s found=%s readable=%s "
        "confidence=%s tokens=%s/%s cached=%s",
        vision_model(), section.pk, question_label, result.get("question_found"),
        result.get("readable"), result.get("confidence"),
        result["usage"]["prompt_tokens"], result["usage"]["completion_tokens"],
        result["usage"]["cached_tokens"],
    )
    return result


def _record_usage(result):
    """Log the cost to the ledger the spend page reads. Never fails the request."""
    from ..models import VisionUsage

    try:
        usage = result["usage"]
        model = result.get("model_used", "")[:64]
        VisionUsage.objects.create(
            hw_check=None, model=model,
            prompt_tokens=usage["prompt_tokens"],
            cached_tokens=usage.get("cached_tokens", 0),
            completion_tokens=usage["completion_tokens"],
            cost_usd=pricing.cost_usd(
                model, usage["prompt_tokens"], usage.get("cached_tokens", 0),
                usage["completion_tokens"], timezone.localdate()),
        )
    except Exception:
        logger.exception("Could not record vision usage for homework help")
