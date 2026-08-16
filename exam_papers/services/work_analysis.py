"""Commentary on a photographed page of a student's working.

Distinct from vision_grading.py, which marks a typed answer against a marking
scheme image. Here the photo *is* the student's work, no mark is awarded, and
the thing being judged is the method: which steps were sound, where it went
wrong, and -- when they have drawn one -- whether the graph is right.

The order of the prompt matters. The model transcribes the page before it
judges anything, and that transcription is shown back to the student. Without
it a student cannot tell "the feedback is wrong about my maths" from "it
misread my 7 as a 1", and one bad read costs their trust in the whole feature.
"""
import json
import logging
import re

from django.conf import settings

from .vision_grading import _vision_completion, encode_image_from_file, vision_model

logger = logging.getLogger(__name__)

# Bigger than the grader's 500: this returns a transcription and per-step
# commentary, not a mark and two sentences.
MAX_TOKENS = 1200

# Copied verbatim from vision_grading.py so both feedback paths render through
# the same KaTeX pass on the page. Diverging here breaks the maths silently.
FORMATTING_RULES = """**Formatting** (the student sees this rendered in a web page - follow exactly):
- Wrap EVERY mathematical expression in single dollar delimiters, e.g. $\\frac{3}{5}$, $m = \\pm 6$
- This includes fractions, symbols and values standing alone in a sentence.
  LaTeX left outside $...$ displays to the student as raw code.
- Do NOT use \\( \\) or \\[ \\] delimiters. Only $...$ and $$...$$.
- Write plain prose sentences. Do NOT use Markdown: no **bold**, no headings,
  no bullet points, no numbered lists."""

DIAGRAM_CHECKLIST = """If the page contains a graph, sketch or diagram, work through this list
explicitly rather than commenting in general terms:
- Are both axes drawn, and labelled with the variable names?
- Is the scale marked, and even along each axis?
- Is the overall shape right for this kind of function?
- Are the intercepts with each axis in the right places?
- Are turning points, maxima and minima in the right places?
- Are asymptotes shown, dashed, and in the right position?
- If the domain is restricted, does the sketch respect it, and are the
  endpoints drawn open or closed correctly?
- Is it a smooth curve where it should be, rather than ruled straight segments?
- Is the curve labelled with its equation?
Only mention the items that are actually worth saying something about."""


def _parse_json_response(raw):
    """Parse the model's JSON, tolerating a fenced or padded response.

    JSON mode is requested, but a fence still shows up occasionally and the
    whole call is wasted if a stray backtick throws it away.
    """
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    fenced = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw, re.DOTALL)
    if fenced:
        return json.loads(fenced.group(1))

    bare = re.search(r'\{.*\}', raw, re.DOTALL)
    if bare:
        return json.loads(bare.group(0))

    raise ValueError(f"Could not parse JSON from response: {raw[:500]}")


def _build_prompt(question_prompt, part_label, expected_answer, has_scheme,
                  max_marks=None):
    estimating = bool(has_scheme and max_marks)
    label = f" part {part_label}" if part_label else ""
    lines = [
        "You are an experienced Leaving Certificate Higher Level Maths teacher, "
        "looking at a photograph of a student's own handwritten working from "
        "their copy. Speak to the student directly, as you would writing in "
        "the margin of their work.",
        "",
        f"**The question{label}:** {question_prompt}",
    ]

    if expected_answer:
        lines += ["", f"**The correct answer:** {expected_answer}"]
    if estimating:
        lines += [
            "",
            "**Marking scheme:** an image of the official marking scheme is "
            f"included, and this part is worth {max_marks} marks. Use the "
            "scheme's own breakdown -- its attempt marks, its partial-credit "
            "scale, what it requires for full marks -- to estimate what this "
            "student's work would earn.",
        ]
    elif has_scheme:
        lines += [
            "",
            "**Marking scheme:** an image of the official marking scheme is "
            "included. Use it to judge whether the method the student used is "
            "one that earns the marks, but do NOT award a mark or a score.",
        ]

    lines += [
        "",
        "**Work through these %s stages in order.**" % ("four" if estimating else "three"),
        "",
        "STAGE 1 - Read the page.",
        "Write down what is on the page, line by line, exactly as the student "
        "wrote it. Do NOT silently correct anything while transcribing: if they "
        "wrote $2x = 6$ then $x = 4$, transcribe both as written. This "
        "transcription is shown back to the student so they can check you read "
        "their handwriting correctly, so it must be faithful rather than tidy.",
        "",
        "STAGE 2 - Judge the method.",
        "For each step, decide whether the approach is mathematically sound "
        "*even if the arithmetic slipped*. A sign error in an otherwise correct "
        "method is a very different thing from the wrong method, and the "
        "student needs to be told which one they have done. Where something "
        "goes wrong, name the line it happens on. Use the language of the "
        "exam: attempt marks, accuracy marks, and what an examiner would give "
        "credit for.",
        "",
        "STAGE 3 - The diagram, if there is one.",
        DIAGRAM_CHECKLIST,
        "",
    ]

    if estimating:
        lines += [
            f"STAGE 4 - Estimate the mark, out of {max_marks}.",
            "Mark the work in front of you the way an examiner would, against "
            "the scheme in the image. Credit a sound method that suffered an "
            "arithmetic slip the way the scheme does -- attempt marks are "
            "earned by the approach, not by the final number. Do not deduct "
            "for untidiness, for skipped lines you can still follow, or for "
            "anything the scheme does not ask for.",
            "",
            f'Put the number in "estimated_mark" as a whole number between 0 '
            f"and {max_marks}, and explain it in \"mark_reasoning\" -- one or "
            "two sentences naming which marks were earned and which were not.",
            "",
            "**The reasoning must not hand over the missing work.** Say "
            '"the scheme wants the discriminant evaluated before you can '
            'claim there are no real roots, and that step is not on your '
            'page" -- not what the discriminant comes to. The same rule that '
            "forbids giving the answer away applies here in full.",
            "",
            "**Withhold the mark rather than guess at one.** If the page is "
            "unreadable, if your confidence is low, if there is no working, or "
            "if you cannot see enough of the page to mark it fairly, set "
            '"estimated_mark" to null and say plainly in "mark_reasoning" '
            "that you could not mark it. A wrong mark from a bad photo is far "
            "worse than no mark: the student is told this is an estimate, and "
            "they will still believe it.",
            "",
        ]

    lines += [
        "**Be honest about what you cannot see.** Never state anything about "
        "working you cannot actually read. If the photo is blurry, angled, cut "
        "off, or the handwriting is ambiguous, say so plainly, set \"readable\" "
        "to false and \"confidence\" to \"low\". Asking for a clearer photo is "
        "far better than guessing at what was written. If the page is blank, or "
        "is not maths working at all, say that and stop.",
        "",
        "**Never give the answer away.** This is the strictest rule here, and "
        "it overrides being helpful. Do NOT state the correct final answer, and "
        "do NOT set out a worked solution or the next line of algebra for them "
        "to copy. Where the student has gone wrong, say what is wrong and what "
        "to reconsider, not what to write. \"Check your arithmetic on the last "
        "line, subtracting 60 from a negative number\" is right; \"the answer is "
        "$-62$\" is not. If the correct answer was supplied to you above, it is "
        "there so you can judge their work, never to be repeated back to them. "
        "The site unlocks full solutions separately, after a student has "
        "genuinely attempted a question, and this feedback must not go around "
        "that.",
        "",
        "**If the page is blank, or shows no working for this question**, set "
        "\"has_working\" to false, say plainly that you cannot see any working, "
        "and leave \"next_step\" as an encouragement to attempt it -- with no "
        "hint as to how.",
        "",
    ]

    if not estimating:
        lines += [
            "**Do not award marks or a score.** This is formative feedback only.",
            "",
        ]

    lines += [
        FORMATTING_RULES,
        "",
        "**Return ONLY a JSON object** with these exact fields:",
        '- "readable": boolean, false if you could not properly read the page',
        '- "has_working": boolean, false if the page is blank or shows no '
        'working for this question',
        '- "confidence": "high", "medium" or "low"',
        '- "transcription": the page as written, newline separated',
        '- "has_diagram": boolean, true if a graph or sketch is present',
        '- "final_answer": the final answer the student reached, or "" if none',
        '- "steps": array of objects, each {"step": what they did, "verdict": '
        'one of "correct"/"slip"/"wrong"/"unclear", "comment": one sentence}',
        '- "method_feedback": one or two short paragraphs of prose on the method',
        '- "diagram_feedback": prose on the graph, or "" if there is no diagram',
        '- "strengths": array of short strings, things they did well',
        '- "next_step": one concrete thing to do next',
    ]

    if estimating:
        lines += [
            f'- "estimated_mark": whole number 0-{max_marks}, or null if you '
            'could not mark it',
            '- "mark_reasoning": one or two sentences justifying that mark, '
            'naming no missing working',
        ]

    return "\n".join(lines)


def _sanitise_mark(result, max_marks):
    """Decide the estimated mark in code, not on the model's say-so.

    The prompt asks for all of this, but a mark is the one output a student
    will take literally, so none of it is left to the model honouring an
    instruction. Anything doubtful becomes no mark at all.
    """
    result["estimated_max_marks"] = max_marks or None

    if not max_marks:
        result["estimated_mark"] = None
        result["mark_reasoning"] = ""
        return

    # A mark read off a page we could not read is the failure this feature was
    # held back for. Refuse it here as well as in the prompt.
    if (not result.get("readable", True)
            or not result.get("has_working", True)
            or (result.get("confidence") or "").lower() == "low"):
        result["estimated_mark"] = None
        return

    raw = result.get("estimated_mark")
    if raw is None or isinstance(raw, bool):
        result["estimated_mark"] = None
        return

    try:
        # Accept "7", 7 and 7.0; a scheme mark is always a whole number.
        mark = int(round(float(raw)))
    except (TypeError, ValueError):
        logger.warning("Discarded unparseable estimated_mark %r", raw)
        result["estimated_mark"] = None
        return

    if not 0 <= mark <= max_marks:
        logger.warning("Discarded out-of-range estimated_mark %r (max %s)", raw, max_marks)
        result["estimated_mark"] = None
        return

    result["estimated_mark"] = mark


def analyse_student_work(work_image_b64, question_prompt, part_label="",
                         question_image=None, marking_scheme_image=None,
                         expected_answer=None, max_marks=None):
    """Analyse a photo of handwritten working.

    Args:
        work_image_b64: base64 JPEG of the student's page (see image_intake).
        question_prompt: text of the question part.
        part_label: e.g. "(b)", for context only.
        question_image / marking_scheme_image: optional ImageFields for context.
        expected_answer: the known answer, if the part has one.
        max_marks: marks this part is worth. Supplied only for exam parts, and
            only alongside a marking scheme -- together they are what switches
            on the estimated mark. Without both, behaviour is unchanged and no
            mark is produced.

    Returns the parsed dict plus 'model_used', 'usage' and a flattened
    'feedback' string. Raises on failure -- the caller decides what the student
    sees, so that no exception text can leak into feedback.
    """
    scheme_b64 = encode_image_from_file(marking_scheme_image) if marking_scheme_image else None

    # No scheme means nothing to mark against, whatever the caller passed.
    if not scheme_b64:
        max_marks = None

    content = [
        {
            "type": "text",
            "text": _build_prompt(question_prompt, part_label, expected_answer,
                                  bool(scheme_b64), max_marks),
        },
        {"type": "text", "text": "**The student's handwritten work:**"},
        {
            "type": "image_url",
            # High detail: this is handwriting, and the whole feature turns on
            # reading it accurately.
            "image_url": {"url": f"data:image/jpeg;base64,{work_image_b64}", "detail": "high"},
        },
    ]

    if question_image:
        question_b64 = encode_image_from_file(question_image)
        if question_b64:
            content += [
                {"type": "text", "text": "**The question, for context:**"},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{question_b64}", "detail": "auto"},
                },
            ]

    if scheme_b64:
        content += [
            {"type": "text", "text": "**The marking scheme, for context:**"},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{scheme_b64}", "detail": "high"},
            },
        ]

    response = _vision_completion(
        messages=[{"role": "user", "content": content}],
        max_tokens=MAX_TOKENS,
        temperature=0.2,
        response_format={"type": "json_object"},
    )

    result = _parse_json_response(response.choices[0].message.content.strip())

    result["model_used"] = vision_model()
    usage = getattr(response, "usage", None)
    result["usage"] = {
        "prompt_tokens": getattr(usage, "prompt_tokens", 0) or 0,
        "completion_tokens": getattr(usage, "completion_tokens", 0) or 0,
    }
    _sanitise_mark(result, max_marks)
    result["feedback"] = compose_feedback(result)

    logger.info(
        "Analysed work photo (%s): readable=%s confidence=%s diagram=%s "
        "mark=%s/%s tokens=%s/%s",
        vision_model(), result.get("readable"), result.get("confidence"),
        result.get("has_diagram"), result.get("estimated_mark"),
        result.get("estimated_max_marks"), result["usage"]["prompt_tokens"],
        result["usage"]["completion_tokens"],
    )
    return result


def compose_feedback(result):
    """Flatten the pieces into one prose string.

    Lets the result drop into the feedback rendering the page already does,
    rather than needing a second maths-rendering path.
    """
    parts = [
        result.get("method_feedback", ""),
        result.get("diagram_feedback", "") if result.get("has_diagram") else "",
        result.get("next_step", ""),
    ]
    return "\n\n".join(p.strip() for p in parts if p and p.strip())
