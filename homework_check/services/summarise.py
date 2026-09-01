"""The 'what to work on' paragraph at the foot of the report.

A separate, text-only call: it reads the assembled findings, not the photos,
so it costs a fraction of a vision call and runs in a second or two. If it
fails for any reason the report still prints -- the caller falls back to
``assembly.fallback_summary``, which only counts what the rows already show.
"""
import logging

from django.conf import settings

from exam_papers.services.vision_grading import (
    LEGACY_PARAM_MODELS, REASONING_TOKEN_BUDGET, get_client,
)
from exam_papers.services.work_analysis import FORMATTING_RULES

logger = logging.getLogger(__name__)

MAX_TOKENS = 400


def chat_model():
    return getattr(settings, "OPENAI_CHAT_MODEL", "gpt-4o-mini")


def _completion(messages, max_tokens, temperature, **extra):
    """Call the chat model with parameters it accepts.

    The same split ``_vision_completion`` makes, for the same reason: newer
    models reject ``max_tokens`` (they want ``max_completion_tokens``) and
    reject any ``temperature`` but the default. Production runs one of those
    as OPENAI_CHAT_MODEL, so getting this wrong is a 400 on every report, not
    an edge case. LEGACY_PARAM_MODELS is imported rather than restated so
    there is one list to keep current.
    """
    model = chat_model()
    kwargs = {"model": model, "messages": messages, **extra}
    kwargs.setdefault("timeout", getattr(settings, "OPENAI_VISION_TIMEOUT", 90))

    if model in LEGACY_PARAM_MODELS:
        kwargs["max_tokens"] = max_tokens
        kwargs["temperature"] = temperature
    else:
        kwargs["max_completion_tokens"] = max(max_tokens, REASONING_TOKEN_BUDGET)

    return get_client().chat.completions.create(**kwargs)


def _findings_text(questions):
    lines = []
    for q in questions:
        bits = [f"{q['label']}: {q['verdict']}"]
        if q["student_answer"]:
            bits.append(f"they answered {q['student_answer']}")
        if q["correct_answer"]:
            bits.append(f"correct answer {q['correct_answer']}")
        if q["comment"]:
            bits.append(q["comment"])
        lines.append(" -- ".join(bits))
    return "\n".join(lines)


def summarise(exercise_name, questions):
    """Two or three sentences for the student. Raises on failure."""
    prompt = "\n".join([
        "You are a Leaving Certificate Higher Level Maths teacher writing the "
        "closing note on a marked homework sheet that is being handed back to "
        "the student.",
        "",
        f"**The exercise:** {exercise_name}",
        "",
        "**What the marking found, question by question:**",
        _findings_text(questions),
        "",
        "Write two or three sentences directly to the student. Say what they "
        "did well first, then name the one or two things most worth working "
        "on -- look for the pattern across questions rather than repeating "
        "the individual comments, which are already printed above your note.",
        "",
        "Do not award a mark, a score, a percentage or a grade. Do not list "
        "the questions again one by one. Do not invent anything that is not in "
        "the findings above.",
        "",
        FORMATTING_RULES,
        "",
        'Return ONLY a JSON object: {"summary": "your two or three sentences"}',
    ])

    response = _completion(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=MAX_TOKENS,
        temperature=0.3,
        response_format={"type": "json_object"},
    )

    import json
    text = str(json.loads(response.choices[0].message.content).get("summary", "")).strip()
    if not text:
        # An empty note would print as a blank line on the sheet. Let the
        # caller fall back to the composed one instead.
        raise ValueError("The summarising call returned no text.")

    usage = getattr(response, "usage", None)
    return text, {
        "prompt_tokens": getattr(usage, "prompt_tokens", 0) or 0,
        "completion_tokens": getattr(usage, "completion_tokens", 0) or 0,
    }
