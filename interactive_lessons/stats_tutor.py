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
            feedback = "Partially correct — one bound is correct."
            hint = "Check your calculation for the other bound."
            auto_score = 0.5
        else:
            base_score = 20
            feedback = "Interval bounds are incorrect."
            hint = "Review the confidence interval formula and recalculate."
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
            feedback = "Partially correct — one element of your answer matches."
            hint = "Recheck coefficients and signs."
        elif student_vals or algebraic_match:
            base_score = 50
            feedback = "Your answer is close but not fully simplified."
            hint = "Try simplifying the expression completely."
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
    """
    prompt = f"""
    You are an experienced Leaving Certificate Higher Level Maths teacher
    grading a student's answer.

    Evaluate numerically and conceptually, but be tolerant of equivalent forms.
    Accept decimals or fractions as equivalent within ±0.02.
    Accept roots in any order.

    Output strict JSON only with:
    - "score": integer 0–100
    - "feedback": concise one-line evaluation
    - "hint": short study tip

    Question: {question_text}
    Correct Answer: {correct_answer}
    Student Answer: {student_answer}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        raw = response.choices[0].message.content.strip()
        json_part = raw[raw.find("{"): raw.rfind("}") + 1]
        data = json.loads(json_part)
        return data.get("score", 0), data.get("feedback", ""), data.get("hint", "")
    except Exception as e:
        return 0, f"Error during grading: {e}", ""
