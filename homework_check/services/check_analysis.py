"""Comparing photos of a student's homework against a worked solutions PDF.

Distinct from ``exam_papers.services.work_analysis``, which comments on the
*method* in a single photo and is careful never to reveal an answer. Here the
audience is a teacher marking a copy, and the output is a page handed back to
the student afterwards, so this prompt **does** state the correct answer.

That inversion is deliberate. It is safe because the same solutions PDF is
already downloadable by any logged-in student from the Downloads menu, so the
report discloses nothing new, and because a teacher reads and can edit every
report before it prints. Do not "fix" this to match work_analysis.py.

Photos are analysed in chunks rather than all at once: sixteen photos plus the
solution pages in one request would run past OPENAI_VISION_TIMEOUT and hold a
web worker open, and there is no background queue in this project.
"""
import json
import logging
import re

from django.conf import settings

from exam_papers.services.vision_grading import (
    _vision_completion, restore_eaten_latex, vision_model,
)
from exam_papers.services.work_analysis import DIAGRAM_CHECKLIST, FORMATTING_RULES

logger = logging.getLogger(__name__)

# Larger than work_analysis's 1200: a chunk covers up to four photos and may
# report on a dozen questions, each with its own answer and comment.
#
# It has to be larger than the *visible* output needs, because the configured
# vision model reasons before it answers and both come out of one budget --
# `_vision_completion` passes this as `max_completion_tokens`. At 3000 the
# effective ceiling was `max(3000, REASONING_TOKEN_BUDGET)` = 4000, and real
# batches of thirteen questions were landing on 3715-3910 of it. The ones that
# tipped over came back HTTP 200 with an empty string where the JSON should be,
# which read to the teacher as "that batch couldn't be read" -- a token ceiling
# wearing the costume of a bad photograph.
MAX_TOKENS = 9000

class EmptyResponse(Exception):
    """The model returned a 200 with no content at all.

    Distinct from a parse failure, because the cause and the cure are
    different: nothing was written, so there is nothing to salvage, and the
    teacher's photographs are not the problem.
    """


VERDICTS = ("correct", "slip", "wrong", "incomplete", "unclear")

# What each verdict is worth when the rating is computed. A slip -- an
# arithmetic or sign error in an otherwise sound method -- is deliberately
# worth half rather than nothing: it is not the same as not knowing how to do
# the question, and a student who keeps slipping needs to hear something
# different from one using the wrong approach.
#
# It is equally deliberately not worth full credit. Counting slips as correct
# would rate a student who got every single answer wrong through sign errors
# as "Excellent", which is not a thing to print and hand to them.
VERDICT_CREDIT = {
    "correct": 1.0,
    "slip": 0.5,
    "incomplete": 0.0,
    "wrong": 0.0,
}

RATING_BANDS = (
    (0.9, "excellent"),
    (0.7, "good"),
    (0.4, "fair"),
)


def _parse_json_response(raw):
    """Parse the model's JSON, tolerating a fenced or padded response.

    JSON mode is requested, but a fence still shows up occasionally and the
    whole call is wasted if a stray backtick throws it away.
    """
    try:
        return restore_eaten_latex(json.loads(raw))
    except json.JSONDecodeError:
        pass

    fenced = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw, re.DOTALL)
    if fenced:
        return restore_eaten_latex(json.loads(fenced.group(1)))

    bare = re.search(r'\{.*\}', raw, re.DOTALL)
    if bare:
        return restore_eaten_latex(json.loads(bare.group(0)))

    raise ValueError(f"Could not parse JSON from response: {raw[:500]}")


def build_prompt(exercise_name, photo_count, page_numbers):
    pages = ", ".join(str(n) for n in page_numbers) or "none supplied"
    return "\n".join([
        "You are an experienced Leaving Certificate Higher Level Maths teacher "
        "marking one student's homework from photographs of their copy. You are "
        "writing for the teacher, and what you write will be printed on a sheet "
        "handed back to the student afterwards.",
        "",
        f"**The exercise:** {exercise_name}",
        f"**Photographs of the student's work:** {photo_count} in this batch.",
        f"**Worked solutions supplied:** page(s) {pages} of the teacher's "
        "solutions PDF, as images.",
        "",
        "**Work through these four stages in order.**",
        "",
        "STAGE 1 - Read the student's pages.",
        "The student has written the question number beside each piece of "
        "working. Find those labels and use them exactly as written, e.g. "
        '"3(b)", "Q7", "12 (ii)". Read what they actually wrote without '
        "silently correcting it: if they wrote $2x = 6$ then $x = 4$, both "
        "lines are what is on the page. Where a question's working runs off "
        "the bottom of one photo and continues on the next, treat it as one "
        'question and set "continues" true.',
        "",
        "STAGE 2 - Find each question in the solutions.",
        "For every question the student attempted, locate that same question in "
        "the supplied solution pages and read the worked answer.",
        "",
        "**If a question is not in the solutions supplied, say so and stop "
        'there for that question:** set "found_in_solutions" to false, put the '
        'student\'s answer in "student_answer", leave "correct_answer" empty, '
        'and set "verdict" to "unclear". Do NOT work the question out '
        "yourself, and do NOT guess at what the answer should be. A confident "
        "wrong answer printed on a sheet and handed to a student is the worst "
        "thing this tool can do. The teacher may simply have scoped the page "
        "range too narrowly, and the report will tell them so.",
        "",
        "STAGE 3 - Compare, question by question.",
        "Does the student's final answer agree with the solution? Is their "
        "method the same one, or a different but valid route to the same "
        "place? Credit a correct alternative method fully -- the solutions "
        "show one way, not the only way. Where they went wrong, name the line "
        "it first goes wrong on, and distinguish these clearly:",
        '- "correct": the answer agrees and the method is sound.',
        '- "slip": the method is sound but an arithmetic or sign error changed '
        "the answer. Say which line.",
        '- "wrong": the method itself is not right for this question.',
        '- "incomplete": they started sensibly but did not finish.',
        '- "unclear": you cannot read it, or it is not in the solutions.',
        "That distinction between a slip and a wrong method is the whole value "
        "of this report -- a student who keeps making sign errors needs to hear "
        "something completely different from one using the wrong approach.",
        "",
        "STAGE 4 - Any graph, sketch or diagram.",
        DIAGRAM_CHECKLIST,
        "",
        "**State the correct answer plainly.** Unlike the tutoring feedback "
        "elsewhere on this site, you SHOULD put the right answer in "
        '"correct_answer" for every question you found in the solutions, '
        "including the ones the student got right. The teacher is marking, and "
        "the student receives this sheet after the homework is over.",
        "",
        "**Do not award marks or a score of any kind.** No marks out of ten, no "
        "percentages, no grades. The comparison and the commentary are the "
        "whole output.",
        "",
        "**Be honest about what you cannot see.** Never state anything about "
        "working you cannot actually read. If a photo is blurry, angled, cut "
        'off, or the handwriting is ambiguous, say so plainly, set "readable" '
        'to false and "confidence" to "low". If a page is blank or is not maths '
        "working at all, report no questions for it rather than inventing any.",
        "",
        "**Every question you report must be one this student actually wrote on "
        "these pages.** Do not list questions from the solutions PDF that the "
        "student did not attempt.",
        "",
        FORMATTING_RULES,
        "",
        "**Return ONLY a JSON object** with these exact fields:",
        '- "readable": boolean, false if you could not properly read the pages',
        '- "confidence": "high", "medium" or "low"',
        '- "has_diagram": boolean, true if a graph or sketch is present',
        '- "diagram_feedback": prose on the graph, or "" if there is none',
        '- "questions": array of objects, each with:',
        '    "label": the question number as the student wrote it',
        '    "found_in_solutions": boolean',
        '    "student_answer": their final answer, or "" if they reached none',
        '    "correct_answer": the answer from the solutions, or "" if not found',
        '    "verdict": one of "correct", "slip", "wrong", "incomplete", "unclear"',
        '    "comment": one or two sentences for the student on what went wrong',
        '    "continues": boolean, true if the working ran on past this batch',
        '- "notes": anything the teacher should know, e.g. a photo that could '
        "not be read or a question missing from the solutions. \"\" if nothing.",
    ])


def _image_part(b64, detail):
    return {
        "type": "image_url",
        "image_url": {"url": f"data:image/jpeg;base64,{b64}", "detail": detail},
    }


def analyse_chunk(photo_b64s, solution_page_b64s, exercise_name,
                  page_numbers=(), chunk_label=""):
    """Compare one batch of photos against the solution pages.

    Args:
        photo_b64s: base64 JPEGs of the student's pages (see image_intake).
        solution_page_b64s: base64 JPEGs of the scoped solution pages.
        exercise_name: what the teacher called this exercise.
        page_numbers: the page numbers those solution images came from.
        chunk_label: e.g. "photos 5-8", for the model's orientation only.

    Returns the parsed dict plus 'model_used' and 'usage'. Raises on failure --
    the caller decides what the teacher sees, so no exception text can leak
    into a report.
    """
    content = [{
        "type": "text",
        "text": build_prompt(exercise_name, len(photo_b64s), page_numbers),
    }]

    heading = f"**The student's work ({chunk_label}):**" if chunk_label \
        else "**The student's work:**"
    content.append({"type": "text", "text": heading})
    for b64 in photo_b64s:
        # High detail: this is handwriting, and the whole thing turns on
        # reading it accurately.
        content.append(_image_part(b64, "high"))

    if solution_page_b64s:
        content.append({"type": "text", "text": "**The worked solutions:**"})
        for b64 in solution_page_b64s:
            content.append(_image_part(b64, "high"))

    response = _vision_completion(
        messages=[{"role": "user", "content": content}],
        max_tokens=MAX_TOKENS,
        temperature=0.2,
        response_format={"type": "json_object"},
    )

    choice = response.choices[0]
    raw = (choice.message.content or "").strip()
    if not raw:
        # Empty body on a 200. The model spent its whole budget reasoning and
        # had none left to answer with; nothing about the photos is at fault,
        # so say so rather than sending the teacher back to re-shoot them.
        usage = getattr(response, "usage", None)
        logger.error(
            "Empty response from %s: finish_reason=%s tokens=%s/%s photos=%s "
            "pages=%s", vision_model(), getattr(choice, "finish_reason", None),
            getattr(usage, "prompt_tokens", 0), getattr(usage, "completion_tokens", 0),
            len(photo_b64s), len(solution_page_b64s),
        )
        raise EmptyResponse(
            "The model ran out of room before it answered. Try again with "
            "fewer photos in the batch, or a narrower page range."
        )

    result = _parse_json_response(raw)
    result["questions"] = _clean_questions(result.get("questions"))

    result["model_used"] = vision_model()
    usage = getattr(response, "usage", None)
    result["usage"] = {
        "prompt_tokens": getattr(usage, "prompt_tokens", 0) or 0,
        "completion_tokens": getattr(usage, "completion_tokens", 0) or 0,
    }

    logger.info(
        "Analysed homework chunk (%s): photos=%s pages=%s readable=%s "
        "confidence=%s questions=%s tokens=%s/%s",
        vision_model(), len(photo_b64s), len(solution_page_b64s),
        result.get("readable"), result.get("confidence"),
        len(result["questions"]), result["usage"]["prompt_tokens"],
        result["usage"]["completion_tokens"],
    )
    return result


def _clean_questions(raw):
    """Coerce the model's question rows into the shape the templates expect.

    A missing key or a verdict the prompt never offered must not reach a page
    a teacher hands to a student, so every field is normalised here rather
    than defended against in five templates.
    """
    cleaned = []
    for row in raw or []:
        if not isinstance(row, dict):
            continue
        label = str(row.get("label") or "").strip()
        if not label:
            continue

        verdict = str(row.get("verdict") or "").strip().lower()
        if verdict not in VERDICTS:
            verdict = "unclear"

        found = bool(row.get("found_in_solutions"))
        correct = str(row.get("correct_answer") or "").strip()
        # An answer for a question the model says it could not find is exactly
        # the invention the prompt forbids. Drop it rather than print it.
        if not found:
            correct = ""
            verdict = "unclear"

        cleaned.append({
            "label": label,
            "found_in_solutions": found,
            "student_answer": str(row.get("student_answer") or "").strip(),
            "correct_answer": correct,
            "verdict": verdict,
            "comment": str(row.get("comment") or "").strip(),
            "continues": bool(row.get("continues")),
        })
    return cleaned
