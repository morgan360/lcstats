from openai import OpenAI
import json

client = OpenAI()

def mark_student_answer(question_text, student_answer, correct_answer, hint_used=False, solution_used=False):
    """
    Evaluate a student's answer to a statistics question using GPT.
    Returns a structured dict: {score, feedback, hint}.
    Applies deductions if the student viewed a hint or solution.
    """

    # Base prompt sent to GPT
    prompt = f"""
    You are an experienced Leaving Certificate Higher Level Maths teacher.

    Evaluate the student's answer to the following question.
    Be concise and constructive.
    Return your response strictly in JSON format with these keys:
    - "score": integer from 0–100
    - "feedback": one-sentence evaluation
    - "hint": one practical study tip (if relevant)

    Question: {question_text}
    Correct Answer: {correct_answer}
    Student Answer: {student_answer}

    Example of correct JSON:
    {{
      "score": 85,
      "feedback": "Good understanding but a small arithmetic slip in calculating the mean.",
      "hint": "Double-check division when computing averages."
    }}
    """

    # Default fallback
    result = {"score": 0, "feedback": "No response from AI.", "hint": ""}

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # fast + inexpensive; change to gpt-5 if preferred
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )

        # Get raw content
        raw = response.choices[0].message.content.strip()

        # Parse JSON safely
        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            # GPT sometimes adds commentary — handle that gracefully
            json_part = raw[raw.find("{"): raw.rfind("}") + 1]
            result = json.loads(json_part) if json_part else {"score": 0, "feedback": raw, "hint": ""}

        # Apply deductions
        deduction = 0
        if hint_used:
            deduction += 20   # -20% if they viewed the hint
        if solution_used:
            deduction += 50   # -50% if they viewed the full solution

        result["score"] = max(0, result.get("score", 0) - deduction)

        # Ensure all keys exist
        result.setdefault("hint", "")
        result.setdefault("feedback", "")

    except Exception as e:
        result = {"score": 0, "feedback": f"Error during grading: {e}", "hint": ""}

    return result
