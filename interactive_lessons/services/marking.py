from interactive_lessons.models import QuestionPart
from sympy import simplify
from sympy.parsing.sympy_parser import (
    parse_expr, standard_transformations,
    implicit_multiplication_application, convert_xor
)
from sympy.core.sympify import SympifyError
from interactive_lessons.services.utils_math import compare_algebraic
from interactive_lessons.stats_tutor import mark_student_answer


# ----------------------------------------------------------------------
# Main grading entry point
# ----------------------------------------------------------------------
def grade_submission(question_part_id, student_answer, hint_used=False, solution_used=False):
    """
    Retrieve the correct answer & question text from the DB,
    perform algebraic check first, then call the local/GPT-based marker.
    """
    try:
        part = QuestionPart.objects.select_related("question").get(id=question_part_id)
    except QuestionPart.DoesNotExist:
        return {"score": 0, "feedback": "Question part not found.", "hint": ""}

    question_text = part.prompt or part.question.text or ""
    correct_answer = part.answer or part.solution or ""

    # --- 1️⃣ Local algebraic equivalence check first ---
    if compare_algebraic(student_answer, correct_answer):
        return {
            "score": 100,
            "is_correct": True,
            "feedback": "Excellent — your algebraic simplification is fully correct.",
            "hint": "Perfect use of like terms and signs.",
        }

    # --- 2️⃣ Otherwise fall back to GPT/local numeric marking ---
    result = mark_student_answer(
        question_text=question_text,
        student_answer=student_answer,
        correct_answer=correct_answer,
        hint_used=hint_used,
        solution_used=solution_used,
    )

    # ensure consistent keys
    result.setdefault("is_correct", result.get("score", 0) >= 90)
    return result
