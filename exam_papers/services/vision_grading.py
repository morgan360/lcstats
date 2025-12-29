"""
GPT-4 Vision-based grading service for exam questions.
Uses marking scheme images to grade student answers.
"""
from openai import OpenAI
import base64
import logging
from django.core.files.storage import default_storage
from django.conf import settings

logger = logging.getLogger(__name__)
client = OpenAI()


def encode_image_from_file(image_field):
    """
    Encode an image field to base64 for OpenAI Vision API.

    Args:
        image_field: Django ImageField

    Returns:
        str: base64 encoded image or None if image doesn't exist
    """
    if not image_field:
        return None

    try:
        # Read the image file
        with default_storage.open(image_field.name, 'rb') as image_file:
            image_data = image_file.read()
            return base64.b64encode(image_data).decode('utf-8')
    except Exception as e:
        logger.error(f"Error encoding image {image_field.name}: {e}")
        return None


def grade_with_vision_marking_scheme(
    student_answer,
    marking_scheme_image,
    question_part_label,
    max_marks,
    question_image=None,
    hint_used=False,
    solution_used=False
):
    """
    Grade a student's answer using GPT-4 Vision to analyze the marking scheme image.

    Args:
        student_answer (str): The student's submitted answer
        marking_scheme_image (ImageField): The marking scheme image for this question part
        question_part_label (str): Part label (e.g., "(a)", "(b)")
        max_marks (int): Maximum marks available for this part
        question_image (ImageField, optional): Image of the question itself
        hint_used (bool): Whether student used a hint
        solution_used (bool): Whether student viewed the solution

    Returns:
        dict: {
            'score': int (0-100 percentage),
            'marks_awarded': float (actual marks out of max_marks),
            'feedback': str (explanation of grading),
            'is_correct': bool
        }
    """

    # Validate inputs
    if not student_answer or not student_answer.strip():
        return {
            'score': 0,
            'marks_awarded': 0.0,
            'feedback': 'No answer provided.',
            'is_correct': False
        }

    if not marking_scheme_image:
        logger.error(f"No marking scheme image for part {question_part_label}")
        return {
            'score': 0,
            'marks_awarded': 0.0,
            'feedback': 'Error: Marking scheme not available. Please contact your teacher.',
            'is_correct': False
        }

    try:
        # Encode the marking scheme image
        marking_scheme_b64 = encode_image_from_file(marking_scheme_image)
        if not marking_scheme_b64:
            raise ValueError("Failed to encode marking scheme image")

        # Build the content array for Vision API
        content = [
            {
                "type": "text",
                "text": f"""You are an experienced Leaving Certificate Higher Level Maths examiner.

**Your Task:** Grade the student's answer for part {question_part_label} using the official marking scheme shown in the image.

**Marking Scheme Image:** The image shows the official LC marking scheme for this question part.

**Student's Answer:** {student_answer}

**Maximum Marks:** {max_marks} marks

**Instructions:**
1. Carefully analyze the marking scheme image to understand what the correct answer should be
2. Compare the student's answer to the marking scheme requirements
3. Award marks according to the marking scheme criteria (including partial credit where appropriate)
4. Be lenient with minor notation differences or equivalent forms
5. Accept algebraically equivalent expressions
6. For numerical answers, accept answers within ±0.02 tolerance

**Important:** Return ONLY a JSON object with these exact fields:
- "marks_awarded": number between 0 and {max_marks} (use decimals for partial credit, e.g., 3.5)
- "feedback": string explaining why marks were awarded/deducted (be concise and constructive)
- "is_correct": boolean (true if marks_awarded >= {max_marks * 0.95}, false otherwise)

Example response:
{{"marks_awarded": 8.5, "feedback": "Correct method and final answer. Minor sign error in step 2 (-0.5 marks).", "is_correct": true}}"""
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{marking_scheme_b64}",
                    "detail": "high"  # Use high detail for better analysis
                }
            }
        ]

        # Optionally include the question image for context
        if question_image:
            question_b64 = encode_image_from_file(question_image)
            if question_b64:
                content.insert(1, {
                    "type": "text",
                    "text": "**Question Image (for context):**"
                })
                content.insert(2, {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{question_b64}",
                        "detail": "auto"
                    }
                })

        # Call GPT-4 Vision API
        response = client.chat.completions.create(
            model=getattr(settings, 'OPENAI_VISION_MODEL', 'gpt-4o'),
            messages=[
                {
                    "role": "user",
                    "content": content
                }
            ],
            max_tokens=500,
            temperature=0.2,  # Low temperature for consistent grading
        )

        # Parse the response
        raw_response = response.choices[0].message.content.strip()

        # Extract JSON from response (handle markdown code blocks)
        import json
        import re

        # Try to find JSON in the response
        json_match = re.search(r'\{[^}]+\}', raw_response, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group(0))
        else:
            raise ValueError(f"Could not parse JSON from response: {raw_response}")

        # Validate required fields
        marks_awarded = float(result.get('marks_awarded', 0))
        feedback = result.get('feedback', 'Answer graded.')
        is_correct = result.get('is_correct', False)

        # Ensure marks don't exceed maximum
        marks_awarded = min(marks_awarded, max_marks)
        marks_awarded = max(marks_awarded, 0)

        # Apply penalty deductions for hint/solution usage
        original_marks = marks_awarded
        if hint_used:
            marks_awarded = marks_awarded * 0.8  # -20%
            feedback += " (Hint penalty: -20%)"
        if solution_used:
            marks_awarded = marks_awarded * 0.5  # -50% (multiplicative with hint)
            feedback += " (Solution penalty: -50%)"

        # Calculate percentage score
        score_percentage = (marks_awarded / max_marks * 100) if max_marks > 0 else 0

        logger.info(
            f"Graded {question_part_label}: {marks_awarded}/{max_marks} "
            f"(original: {original_marks}, hint: {hint_used}, solution: {solution_used})"
        )

        return {
            'score': int(score_percentage),
            'marks_awarded': round(marks_awarded, 2),
            'feedback': feedback,
            'is_correct': is_correct and not (hint_used or solution_used)  # Not correct if used help
        }

    except Exception as e:
        logger.error(f"Error grading with vision API for {question_part_label}: {e}", exc_info=True)
        return {
            'score': 0,
            'marks_awarded': 0.0,
            'feedback': f'Grading error: {str(e)}. Please try again or contact support.',
            'is_correct': False
        }
