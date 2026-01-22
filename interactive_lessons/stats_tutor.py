from openai import OpenAI
from fractions import Fraction
import json, re, math
from interactive_lessons.services.utils_math import compare_algebraic

client = OpenAI()

def parse_interval(answer):
    """
    Extract interval notation from student answers.
    Handles formats like:
    - (58.98, 63.03)
    - 58.98 < μ < 63.03
    - 58.98 < mu < 63.03
    - [58.98, 63.03]
    Returns (lower, upper) as floats, or None if not an interval.
    """
    if not answer:
        return None

    answer = answer.strip()

    # Format 1: Parentheses/brackets notation (58.98, 63.03) or [58.98, 63.03]
    match = re.search(r'[\(\[]?\s*(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\s*[\)\]]?', answer)
    if match:
        try:
            lower = float(match.group(1))
            upper = float(match.group(2))
            return (lower, upper)
        except:
            pass

    # Format 2: Inequality notation: 58.98 < μ < 63.03 or 58.98 < mu < 63.03
    match = re.search(r'(-?\d+\.?\d*)\s*<\s*[μµmu]+\s*<\s*(-?\d+\.?\d*)', answer)
    if match:
        try:
            lower = float(match.group(1))
            upper = float(match.group(2))
            return (lower, upper)
        except:
            pass

    return None

def normalise_numeric_answer(answer):
    """
    Extract numeric values (fractions, decimals, degrees, radians) from a student's answer string.
    Returns a sorted list of floats in radians for easy comparison.
    """
    if not answer:
        return []

    answer = answer.strip()

    # Convert unicode superscripts to regular power notation
    # e.g., "2⁵" → "2^5", "x²" → "x^2"
    _SUPERSCRIPTS = {
        "⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4",
        "⁵": "5", "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9",
        "⁺": "+", "⁻": "-", "⁽": "(", "⁾": ")",
        "ⁿ": "n", "/": "/"
    }
    superscript_buffer = []
    result = []
    for c in answer:
        if c in _SUPERSCRIPTS:
            superscript_buffer.append(_SUPERSCRIPTS[c])
        else:
            if superscript_buffer:
                result.append("^" + "".join(superscript_buffer))
                superscript_buffer = []
            result.append(c)
    if superscript_buffer:
        result.append("^" + "".join(superscript_buffer))
    answer = "".join(result)

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


def compare_answers(student_ans, correct_ans, tol=0.02):
    """
    Compare two lists of numeric answers, order-independent, within a tolerance.
    Returns a score fraction (1.0 = perfect match, 0.5 = one correct, 0 = none).
    """
    if not student_ans or not correct_ans:
        return 0.0

    matched = 0
    used = set()
    for s in student_ans:
        for i, c in enumerate(correct_ans):
            if i not in used and math.isclose(s, c, abs_tol=tol):
                matched += 1
                used.add(i)
                break

    return matched / len(correct_ans)


def mark_student_answer(question_text, student_answer, correct_answer,
                        hint_used=False, solution_used=False):
    # --- 1️⃣ Check for interval notation first ---
    student_interval = parse_interval(student_answer)
    correct_interval = parse_interval(correct_answer)

    if student_interval and correct_interval:
        # Compare intervals
        lower_match = math.isclose(student_interval[0], correct_interval[0], abs_tol=0.02)
        upper_match = math.isclose(student_interval[1], correct_interval[1], abs_tol=0.02)

        if lower_match and upper_match:
            base_score = 100
            feedback = "Excellent — confidence interval is correct!"
            hint = "Well done! Both bounds are accurate."
            auto_score = 1.0
        elif lower_match or upper_match:
            base_score = 50
            if lower_match:
                feedback = f"Partially correct. Your lower bound ({student_interval[0]:.2f}) is correct, but the upper bound is incorrect. The correct upper bound is {correct_interval[1]:.2f}."
                hint = "Double-check your calculation for the upper bound. Remember: upper bound = mean + (critical value × standard error)."
            else:
                feedback = f"Partially correct. Your upper bound ({student_interval[1]:.2f}) is correct, but the lower bound is incorrect. The correct lower bound is {correct_interval[0]:.2f}."
                hint = "Double-check your calculation for the lower bound. Remember: lower bound = mean - (critical value × standard error)."
            auto_score = 0.5
        else:
            base_score = 20
            feedback = f"Both interval bounds are incorrect. You calculated ({student_interval[0]:.2f}, {student_interval[1]:.2f}), but the correct interval is ({correct_interval[0]:.2f}, {correct_interval[1]:.2f})."
            hint = "Review the confidence interval formula: CI = x̄ ± (critical value × SE). Check that you're using the correct critical value and standard error calculation."
            auto_score = 0.0
    else:
        # --- 2️⃣ Local numeric or algebraic check ---
        student_vals = normalise_numeric_answer(student_answer)
        correct_vals = normalise_numeric_answer(correct_answer)

        auto_score = compare_answers(student_vals, correct_vals)

        # ✅ Algebraic check fallback if numeric failed
        algebraic_match = False
        if auto_score == 0 and student_answer and correct_answer:
            algebraic_match = compare_algebraic(student_answer, correct_answer)
            if algebraic_match:
                auto_score = 1.0

        # --- 3️⃣ Quick results if clear match ---
        if auto_score == 1.0:
            base_score = 100
            feedback = "Excellent — fully correct algebraic simplification."
            hint = "Well done! You simplified accurately."
        elif auto_score >= 0.5:
            base_score = 70
            num_correct = int(auto_score * len(correct_vals))
            num_total = len(correct_vals)
            feedback = f"Partially correct — you got {num_correct} out of {num_total} values correct. Your work shows understanding, but double-check your calculations."
            hint = "Review each part of your answer carefully. Check for sign errors, calculation mistakes, or values that might need further simplification."
        elif student_vals:
            base_score = 50
            feedback = f"Your answer is numerically close but doesn't match the expected result. You entered {student_vals}, but this doesn't match the correct answer format."
            hint = "Check if you need to simplify further, combine like terms, or express your answer in a different form (e.g., as a fraction, in simplified radical form, or factored)."
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

    FEEDBACK REQUIREMENTS:
    When the answer is INCORRECT, your feedback must be:
    1. SPECIFIC - Identify exactly what went wrong (calculation error, wrong formula, sign error, etc.)
    2. EDUCATIONAL - Explain WHY it's wrong in a way that helps them understand
    3. CONSTRUCTIVE - Give a clear next step or hint about what to try
    4. ENCOURAGING - Acknowledge any correct elements even if final answer is wrong

    Output strict JSON with these fields:
    - "score": integer 0–100 (award partial credit generously for correct approach)
    - "feedback": 2-3 sentences explaining what's wrong and why
    - "hint": Specific actionable hint for what to do next (e.g., "Check your sign when expanding the brackets" or "Remember to convert to radians before using the formula")
    - "common_mistake": (optional) If this is a common error, name it (e.g., "Sign error", "Wrong formula", "Calculation mistake")

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
            model="gpt-4o-mini",
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
