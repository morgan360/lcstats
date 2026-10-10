from openai import OpenAI
from fractions import Fraction
import json, re, math
from django.conf import settings
from interactive_lessons.services.utils_math import compare_algebraic, latex_to_plain
from exam_papers.services.vision_grading import restore_eaten_latex

client = OpenAI()


def grading_model():
    """Model used for GPT answer grading (OPENAI_GRADING_MODEL in .env)."""
    return getattr(settings, "OPENAI_GRADING_MODEL", "gpt-4o-mini")

_OPEN, _CLOSE = "([", ")]"


def _top_level_pairs(text):
    """[(start, end, first, second)] for each outermost bracket group that holds
    exactly one top-level comma: (58.98, 63.03), [-1, 1], and also the
    (((1)/(3)), -2) that latex_to_plain makes of (\\frac{1}{3}, -2), whose
    fractions bring brackets of their own. "(1, 2), (3, 4)" gives two."""
    found, depth, start, commas = [], 0, None, []
    for i, ch in enumerate(text):
        if ch in _OPEN:
            if depth == 0:
                start, commas = i, []
            depth += 1
        elif ch in _CLOSE and depth:
            depth -= 1
            if depth == 0 and len(commas) == 1:
                found.append((start, i + 1, text[start + 1:commas[0]], text[commas[0] + 1:i]))
        elif ch == "," and depth == 1:
            commas.append(i)
    return found


# a < x < b, for any variable name: 58.98 < μ < 63.03, 0.81 < p < 0.874.
_BETWEEN_RE = re.compile(r"^\s*([^<>]+?)\s*<\s*[^<>\d]+?\s*<\s*([^<>]+?)\s*$")


def _single_number(text):
    """The one value in ``text`` (fractions, decimals, pi, LaTeX), or None."""
    values = normalise_numeric_answer(text)
    return values[0] if len(values) == 1 else None


def parse_pairs(answer):
    """Every bracketed ``(a, b)`` in an answer, in order, as float tuples.

    [] when there is none, or when any half cannot be read as a number -- a
    pair that half-parses must not be compared as if it were the whole answer.
    """
    pairs = []
    for _, _, left, right in _top_level_pairs(latex_to_plain(answer or "")):
        first, second = _single_number(left), _single_number(right)
        if first is None or second is None:
            return []
        pairs.append((first, second))
    return pairs


def parse_interval(answer):
    """One ordered pair from an answer: an interval or a single point.

    Accepts a bracketed pair, ``a < x < b``, or a bare ``a, b`` (a student
    leaving the brackets off). Returns (first, second), or None.

    Used only when the *stored* answer is one bracketed pair or an inequality.
    It once ran on every answer containing a comma, so a list of roots was
    marked as an interval: in order, and on its first two numbers only.
    """
    if not answer:
        return None
    pairs = parse_pairs(answer)
    if pairs:
        return pairs[0] if len(pairs) == 1 else None
    plain = latex_to_plain(answer.strip())
    between = _BETWEEN_RE.match(plain)
    if between:
        low, high = _single_number(between.group(1)), _single_number(between.group(2))
        return (low, high) if low is not None and high is not None else None
    halves = [h for h in re.split(r"[,;]", plain) if h.strip()]
    if len(halves) == 2:
        first, second = _single_number(halves[0]), _single_number(halves[1])
        if first is not None and second is not None:
            return (first, second)
    return None


def _stored_pair(correct_answer):
    """The stored answer as one ordered pair, if that is all it is.

    "(5/6, 49/12)" or "0.81 < p < 0.874" qualifies; "Period = 120°, Range:
    [-1, 1]" does not, or the range alone would earn full marks.
    """
    plain = latex_to_plain((correct_answer or "").strip())
    pairs = parse_pairs(correct_answer)
    if len(pairs) == 1:
        start, end, _, _ = _top_level_pairs(plain)[0]
        rest = plain[:start] + plain[end:]
        return pairs[0] if not re.sub(r"[\s$.]", "", rest) else None
    if pairs:
        return None
    between = _BETWEEN_RE.match(latex_to_plain((correct_answer or "").strip()))
    return parse_interval(correct_answer) if between else None


def _stored_points(correct_answer):
    """The stored answer as a set of points, if that is all it holds.

    Labels may sit around them ("Maximum: (-1/3, -22/27), Minimum: (1, -2)"),
    but not other numbers: "Period = 120°, Range: [-1, 1]" is not a set of
    points, and the range alone must not earn its full marks.
    """
    plain = latex_to_plain((correct_answer or "").strip())
    groups = _top_level_pairs(plain)
    pairs = parse_pairs(correct_answer)
    if not pairs:
        return []
    rest, last = [], 0
    for start, end, _, _ in groups:
        rest.append(plain[last:start])
        last = end
    rest.append(plain[last:])
    return [] if re.search(r"\d", "".join(rest)) else pairs


def compare_pairs(student_pairs, correct_pairs):
    """Score a set of points: each must match a stored point in both coordinates.

    The points may come in any order; a point's own coordinates may not.
    Extra points count against the score, as extra values do in compare_answers.
    """
    if not student_pairs or not correct_pairs:
        return 0.0
    matched, used = 0, set()
    for sx, sy in student_pairs:
        for i, (cx, cy) in enumerate(correct_pairs):
            if (i not in used and abs(sx - cx) <= _tolerance(cx)
                    and abs(sy - cy) <= _tolerance(cy)):
                matched += 1
                used.add(i)
                break
    return matched / max(len(student_pairs), len(correct_pairs))


def normalise_numeric_answer(answer):
    """
    Extract numeric values (fractions, decimals, degrees, radians) from a student's answer string.
    Returns a sorted list of floats in radians for easy comparison.
    """
    if not answer:
        return []

    # MathLive sends LaTeX: \frac{2}{15} must read as 2/15, not be dropped.
    answer = latex_to_plain(answer.strip())

    # Convert unicode superscripts to regular power notation
    # e.g., "2⁵" → "2^(5)", "x²" → "x^(2)", "2⁵/²" → "2^(5/2)"
    _SUPERSCRIPTS = {
        "⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4",
        "⁵": "5", "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9",
        "⁺": "+", "⁻": "-", "⁽": "(", "⁾": ")",
        "ⁿ": "n",
    }

    def _is_superscript(i):
        return 0 <= i < len(answer) and answer[i] in _SUPERSCRIPTS

    superscript_buffer = []
    result = []
    for i, c in enumerate(answer):
        if c in _SUPERSCRIPTS:
            superscript_buffer.append(_SUPERSCRIPTS[c])
        elif c == "/" and superscript_buffer and _is_superscript(i + 1):
            # Superscript fraction, e.g. "2⁵/²" → "2^(5/2)". Only a slash that
            # sits between two superscripts belongs to the exponent; anywhere
            # else it is ordinary division and must be left alone.
            superscript_buffer.append("/")
        else:
            if superscript_buffer:
                result.append("^(" + "".join(superscript_buffer) + ")")
                superscript_buffer = []
            result.append(c)
    if superscript_buffer:
        result.append("^(" + "".join(superscript_buffer) + ")")
    answer = "".join(result)

    # Units the format line already names: "€2,463.32" and "6.17%" are the
    # numbers 2463.32 and 6.17. A percentage is not turned into a decimal --
    # questions that want a rate as a percentage store it as one.
    answer = answer.replace("€", "").replace("£", "").replace("\\%", "").replace("%", "")

    # replace degree symbol with radians equivalent
    answer = answer.replace("°", "*pi/180")

    # handle common forms of pi
    answer = re.sub(r"(?<![a-zA-Z])π", "pi", answer)

    # remove labels like x=, X=, etc.
    answer = re.sub(r"[xX=]", "", answer)

    # split on commas/semicolons
    parts = re.split(r"[,;]+", answer)
    parts = [p.strip() for p in parts if p.strip()]

    values = []
    for p in parts:
        try:
            from sympy import sympify
            val = float(sympify(p).evalf())  # evaluate radians/π etc.
            values.append(val)
        except Exception:
            try:
                values.append(float(Fraction(p)))
            except Exception:
                continue

    return sorted(values)


def _tolerance(correct, tol=0.02):
    """How far a student's number may be from ``correct`` and still match.

    A flat +-0.02 is right for answers of 2 or more but far too loose for small
    ones: it passed 12/52 (0.231) for 1/4, and would pass any answer under 0.02
    for a probability of 1/270725. So it shrinks with the answer while still
    accepting one rounded to 2 decimal places (0.13 for 2/15). A miss is not
    marked wrong; it goes on to GPT.
    """
    size = abs(correct)
    if size >= 2:
        return tol
    if size >= 0.5:
        return min(tol, 0.01 * size)
    if size >= 0.01:
        return min(tol, 0.005)
    return 0.02 * size if size else 1e-9


def compare_answers(student_ans, correct_ans, tol=0.02):
    """
    Compare two lists of numeric answers, order-independent, within a tolerance
    that scales with each correct value (see _tolerance).
    Returns a score fraction (1.0 = perfect match, 0.5 = one correct, 0 = none).
    Extra values count against it: "1, -2, 5" for a stored "1, -2" is 2/3,
    not a full match.
    """
    if not student_ans or not correct_ans:
        return 0.0

    matched = 0
    used = set()
    for s in student_ans:
        for i, c in enumerate(correct_ans):
            if i not in used and abs(s - c) <= _tolerance(c, tol):
                matched += 1
                used.add(i)
                break

    return matched / max(len(student_ans), len(correct_ans))


def compare_ignoring_one_sided_degrees(student_answer, correct_answer):
    """Score ``53`` against a stored ``53°`` (or the reverse) as a match.

    normalise_numeric_answer reads ° as *pi/180, which is right when both sides
    carry it but makes a bare 53 and 53° differ by a factor of 57. A wrong
    numeric answer is scored 50 without GPT, so that mismatch failed students
    who left the degree sign off. When exactly one side has one, compare the
    numbers with the sign dropped from both. Returns None when it does not apply.
    """
    student_plain = latex_to_plain((student_answer or "").strip())
    correct_plain = latex_to_plain((correct_answer or "").strip())
    if ("°" in student_plain) == ("°" in correct_plain):
        return None
    return compare_answers(normalise_numeric_answer(student_plain.replace("°", "")),
                           normalise_numeric_answer(correct_plain.replace("°", "")))


def _same_text(student_answer, correct_answer):
    """True when the student typed the stored answer, give or take spaces,
    dollar signs and case. Answers such as two line equations or a labelled
    period and range parse as neither numbers nor pairs; copied exactly they
    are right, and need no GPT call to say so."""
    def squash(text):
        return re.sub(r"[\s$]", "", text or "").lower()
    return bool(squash(correct_answer)) and squash(student_answer) == squash(correct_answer)


_THOUSANDS = re.compile(r"(?<![\d.])(\d{1,3}(?:,\d{3})+)(?![\d,])")


def _drop_thousands_commas(student_answer, correct_answer):
    """Read "2,492.36" as one number when one number is what is stored.

    Only then: against a stored list, "30,150" is two angles, not 30150.
    """
    if not student_answer or len(normalise_numeric_answer(correct_answer)) != 1:
        return student_answer
    return _THOUSANDS.sub(lambda m: m.group(1).replace(",", ""), student_answer)


def mark_student_answer(question_text, student_answer, correct_answer,
                        hint_used=False, solution_used=False):
    student_answer = _drop_thousands_commas(student_answer, correct_answer)
    if _same_text(student_answer, correct_answer):
        deduction = (20 if hint_used else 0) + (50 if solution_used else 0)
        return {"score": max(0, 100 - deduction),
                "feedback": "Excellent — fully correct!", "hint": "Well done!"}

    # --- 1️⃣ One ordered pair: an interval or a single point ---
    # Decided by the stored answer's shape, never the student's: a bare list
    # of roots is not an interval, whatever the student typed.
    correct_interval = _stored_pair(correct_answer)
    student_interval = parse_interval(student_answer) if correct_interval else None
    correct_points = [] if correct_interval else _stored_points(correct_answer)

    if student_interval and correct_interval:
        # Compare intervals
        lower_match = math.isclose(student_interval[0], correct_interval[0], abs_tol=0.02)
        upper_match = math.isclose(student_interval[1], correct_interval[1], abs_tol=0.02)

        if lower_match and upper_match:
            base_score = 100
            feedback = "Excellent — both values are correct!"
            hint = "Well done!"
            auto_score = 1.0
        elif lower_match or upper_match:
            base_score = 50
            if lower_match:
                feedback = f"Partially correct. Your first value ({student_interval[0]:.2f}) is correct, but the second is not. The correct second value is {correct_interval[1]:.2f}."
                hint = "Check your working for the second value."
            else:
                feedback = f"Partially correct. Your second value ({student_interval[1]:.2f}) is correct, but the first is not. The correct first value is {correct_interval[0]:.2f}."
                hint = "Check your working for the first value."
            auto_score = 0.5
        else:
            base_score = 20
            feedback = f"Both values are incorrect. You gave ({student_interval[0]:.2f}, {student_interval[1]:.2f}), but the correct answer is ({correct_interval[0]:.2f}, {correct_interval[1]:.2f})."
            hint = "Check the order of the two values, and your working for each."
            auto_score = 0.0
    else:
        # --- 2️⃣ Local check: several points, or a list of values ---
        if correct_points:
            student_vals = parse_pairs(student_answer)
            correct_vals = correct_points
            auto_score = compare_pairs(student_vals, correct_vals)
        else:
            student_vals = normalise_numeric_answer(student_answer)
            correct_vals = normalise_numeric_answer(correct_answer)
            auto_score = compare_answers(student_vals, correct_vals)
        if auto_score < 1.0:
            degrees_score = compare_ignoring_one_sided_degrees(student_answer, correct_answer)
            if degrees_score is not None:
                auto_score = max(auto_score, degrees_score)

        # ✅ Algebraic check fallback if numeric failed
        algebraic_match = False
        if auto_score == 0 and student_answer and correct_answer:
            algebraic_match = compare_algebraic(student_answer, correct_answer)
            if algebraic_match:
                auto_score = 1.0

        # --- 3️⃣ Quick results if clear match ---
        if auto_score == 1.0:
            base_score = 100
            feedback = "Excellent — fully correct!"
            hint = "Well done!"
        elif auto_score >= 0.5:
            base_score = 70
            # Use GPT for educational feedback on partial answers
            _, feedback, hint = gpt_grade(question_text, student_answer, correct_answer)
        elif student_vals and correct_vals:
            # Only when the stored answer parsed: against one that did not
            # ("x=√2, y=2√2, z=√6"), a right answer scored a flat 50 here.
            base_score = 50
            # Use GPT for educational feedback on wrong numeric answers
            _, feedback, hint = gpt_grade(question_text, student_answer, correct_answer)
        else:
            # fallback to GPT if neither numeric nor algebraic match
            base_score, feedback, hint = gpt_grade(question_text, student_answer, correct_answer)

    # --- 3️⃣ Apply deductions for hint/solution use ---
    deduction = 0
    if hint_used:
        deduction += 20
    if solution_used:
        deduction += 50

    final_score = max(0, base_score - deduction)

    return {
        "score": final_score,
        "feedback": feedback,
        "hint": hint
    }



def gpt_grade(question_text, student_answer, correct_answer):
    """
    Uses GPT as a fallback for conceptual / algebraic answers.
    Provides detailed, educational feedback to help students learn.
    """
    prompt = f"""
    You are an experienced Leaving Certificate Higher Level Maths teacher
    grading a student's answer. Your goal is to help the student LEARN, not just
    tell them they're wrong.

    EVALUATION CRITERIA:
    - Be tolerant of equivalent forms (decimals ≈ fractions within ±0.02)
    - Accept roots/solutions in any order
    - Accept algebraically equivalent expressions
    - Award partial credit for correct approach or partially correct work

    SCORING RULES (apply strictly — only the final answer is captured, never
    the student's working, so do not infer method that is not visible):
    - Blank, placeholder or meaningless input (e.g. "-", "\\cdot", empty LaTeX
      placeholders such as \\frac{{\\placeholder{{}}}}{{\\placeholder{{}}}}): score 0
    - Numerically equivalent to the correct answer, including rounding or
      decimal-versus-surd form (e.g. 2.8 for $2\\sqrt{{2}}$): score 90-100
    - BUT where the question asks for a particular FORM, that form is the
      answer and a number is not it. "Express $\\log_9 40$ in terms of
      logarithms base 3", "give your answer in the form $an^2 + bn + c$",
      "leave your answer in surd form": an answer that is numerically right
      but in the wrong form shows the work was done, not the thing asked, so
      score 20-40 and name the form that was wanted in the feedback.
    - The answer editor writes $\\pm$ and $\\mp$ as stacked fractions, so
      \\frac{{+}}{{-}} and \\frac{{-}}{{+}} are those symbols and not division:
      read \\frac{{-}}{{+}}8i as $\\pm 8i$. Either stacking gives the same pair
      of roots, so accept both against a $\\pm$ answer. This applies ONLY when
      the numerator and denominator are the signs themselves. Anything else --
      \\frac{{2}}{{6}}, \\frac26 -- is an ordinary fraction and is read as
      division, exactly as written.
    - Correct final answer expressed differently (equivalent algebraic form,
      solutions in another order): score 90-100

    FEEDBACK REQUIREMENTS:
    When the answer is INCORRECT, your feedback must be:
    1. SPECIFIC - Identify exactly what went wrong (calculation error, wrong formula, sign error, etc.)
    2. EDUCATIONAL - Explain WHY it's wrong in a way that helps them understand
    3. CONSTRUCTIVE - Give a clear next step or hint about what to try
    4. ENCOURAGING - Acknowledge any correct elements even if final answer is wrong

    FORMATTING (the student sees this rendered in a web page - follow exactly):
    - Wrap EVERY mathematical expression in single dollar delimiters: $\\frac{{3}}{{5}}$
    - This includes fractions, probabilities and symbols standing alone in a
      sentence. Never leave LaTeX such as \\frac{{3}}{{5}} outside $...$ - it
      shows to the student as raw code.
    - Do NOT use \\( \\) or \\[ \\] delimiters. Only $...$ and $$...$$.
    - Write plain prose sentences. Do NOT use Markdown: no **bold**, no
      headings, no bullet points, no numbered step lists.

    Output strict JSON with these fields, IN THIS ORDER. The feedback
    comes before the score so the score follows the reasoning rather than
    being committed to ahead of it:
    - "feedback": 2-3 sentences explaining what's wrong and why
    - "hint": ONE or TWO sentences nudging them toward the next step. It is a
      hint, not a worked solution: name the idea or rule to apply, never lay out
      the full method or do the steps for them. (e.g., "Check your sign when
      expanding the brackets" or "Remember to convert to radians before using
      the formula")
    - "common_mistake": (optional) If this is a common error, name it (e.g., "Sign error", "Wrong formula", "Calculation mistake")
    - "score": integer 0–100 (award partial credit generously for correct approach)

    EXAMPLES OF GOOD FEEDBACK:
    - "Your approach is correct, but there's a calculation error. You correctly identified the quadratic formula, but when calculating the discriminant, you used b=3 instead of b=-3. This changes the sign. Try recalculating with the correct sign."
    - "You're very close! The first part of your answer is correct, but you forgot to simplify the square root. √18 can be simplified to 3√2. Always check if you can simplify radicals."
    - "This suggests you used the wrong formula. This is a permutation problem (order matters), not a combination. Try using nPr instead of nCr."

    Question: {question_text}
    Correct Answer: {correct_answer}
    Student Answer: {student_answer}
    """

    try:
        response = client.chat.completions.create(
            model=grading_model(),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        raw = response.choices[0].message.content.strip()

        # Parse JSON with better error handling
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            # Fallback: try to extract JSON from markdown code blocks
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
            else:
                # Last resort: try to find any JSON object
                json_match = re.search(r'\{.*\}', raw, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group(0))
                else:
                    raise
        # "\frac" in the model's JSON parses as formfeed + "rac"
        data = restore_eaten_latex(data)

        # Extract the enhanced feedback components
        score = data.get("score", 0)
        feedback = data.get("feedback", "Your answer is incorrect.")
        hint = data.get("hint", "Review the relevant notes and try again.")
        common_mistake = data.get("common_mistake", "")

        # Combine feedback with common mistake if present
        if common_mistake:
            feedback = f"[{common_mistake}] {feedback}"

        return score, feedback, hint
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"GPT grading error: {e}. Question: {question_text}, Student: {student_answer}, Correct: {correct_answer}")
        return 0, f"Unable to grade this answer automatically. Please review your work and try again.", "Check your calculation step-by-step."
