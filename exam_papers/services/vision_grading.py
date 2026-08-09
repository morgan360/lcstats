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

# Built on first use, not at import. A module-level OpenAI() raises without an
# API key in the environment, which made this module unimportable in tests --
# and settings.py says the same thing about not building clients at import time.
_client = None


def get_client():
    global _client
    if _client is None:
        _client = OpenAI()
    return _client

# Models that take the older completion parameters. Newer models reject
# max_tokens (they want max_completion_tokens) and reject any temperature
# other than the default, so the call has to be shaped per model.
LEGACY_PARAM_MODELS = {'gpt-4o', 'gpt-4o-mini', 'gpt-4', 'gpt-4-turbo'}

# Reasoning models spend part of their completion budget thinking before any
# visible output, so a budget sized for the answer alone comes back empty.
REASONING_TOKEN_BUDGET = 4000


def vision_model():
    return getattr(settings, 'OPENAI_VISION_MODEL', 'gpt-4o')


def _vision_completion(messages, max_tokens, temperature, **extra):
    """Call the configured vision model with parameters it accepts."""
    model = vision_model()
    kwargs = {'model': model, 'messages': messages, **extra}

    # Without this a stalled call holds a web worker open indefinitely: these
    # run synchronously in the request, and there is no background queue.
    kwargs.setdefault('timeout', getattr(settings, 'OPENAI_VISION_TIMEOUT', 90))

    if model in LEGACY_PARAM_MODELS:
        kwargs['max_tokens'] = max_tokens
        kwargs['temperature'] = temperature
    else:
        kwargs['max_completion_tokens'] = max(max_tokens, REASONING_TOKEN_BUDGET)

    return get_client().chat.completions.create(**kwargs)


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


def extract_max_marks_from_scheme(marking_scheme_image, question_part_label):
    """
    Extract maximum marks from a marking scheme image using GPT-4 Vision.

    Args:
        marking_scheme_image (ImageField): The marking scheme image
        question_part_label (str): Part label (e.g., "(a)", "(b)")

    Returns:
        int: Extracted max marks, or None if extraction fails
    """
    if not marking_scheme_image:
        return None

    try:
        scheme_b64 = encode_image_from_file(marking_scheme_image)
        if not scheme_b64:
            return None

        response = _vision_completion(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"""You are analyzing a Leaving Certificate marking scheme image.

**Task:** Extract the maximum marks available for part {question_part_label}.

**How marks are written in these schemes:** the Marking Notes column gives a
scale, not a mark count - "Scale 10C (0, 3, 7, 10)" means the part is worth 10
marks, awarded at 0, 3, 7 or 10. The number in the scale name is the maximum,
and it is always the last number in the bracketed list. Read the maximum from
there.

**Do not** use the "Model Solution - N Marks" heading: that is the total for the
whole question, not for this part.

**Instructions:**
1. Find the scale for part {question_part_label}
2. Take its maximum as described above
3. Return ONLY a JSON object with one field: "max_marks" (integer)

Example: for "Scale 10C (0, 3, 7, 10)" respond {{"max_marks": 10}}

If there is no scale for this part, return: {{"max_marks": 0}}"""
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{scheme_b64}",
                                "detail": "high"
                            }
                        }
                    ]
                }
            ],
            max_tokens=100,
            temperature=0.1,
            response_format={"type": "json_object"}
        )

        raw_response = response.choices[0].message.content.strip()

        # Parse JSON with robust error handling
        import json
        import re

        try:
            result = json.loads(raw_response)
        except json.JSONDecodeError:
            # Fallback to regex extraction
            json_match = re.search(r'\{.*\}', raw_response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(0))
            else:
                logger.warning(f"Could not parse JSON for max_marks extraction: {raw_response}")
                return None

        max_marks = int(result.get('max_marks', 0))
        if max_marks > 0:
            logger.info(f"Extracted max_marks={max_marks} for {question_part_label}")
            return max_marks

        logger.warning(f"Could not extract max_marks for {question_part_label}")
        return None

    except Exception as e:
        logger.error(f"Error extracting max_marks for {question_part_label}: {e}")
        return None


def grade_with_vision_marking_scheme(
    student_answer,
    marking_scheme_image,
    question_part_label,
    max_marks=None,
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
        max_marks (int, optional): Maximum marks available for this part (auto-extracted if None)
        question_image (ImageField, optional): Image of the question itself
        hint_used (bool): Whether student used a hint
        solution_used (bool): Whether student viewed the solution

    Returns:
        dict: {
            'score': int (0-100 percentage),
            'marks_awarded': float (actual marks out of max_marks),
            'feedback': str (explanation of grading),
            'is_correct': bool,
            'max_marks': int (extracted or provided max marks)
        }
    """

    # Validate inputs
    if not student_answer or not student_answer.strip():
        return {
            'score': 0,
            'marks_awarded': 0.0,
            'feedback': 'No answer provided.',
            'is_correct': False,
            'max_marks': max_marks or 0
        }

    if not marking_scheme_image:
        logger.error(f"No marking scheme image for part {question_part_label}")
        return {
            'score': 0,
            'marks_awarded': 0.0,
            'feedback': 'Error: Marking scheme not available. Please contact your teacher.',
            'is_correct': False,
            'max_marks': max_marks or 0
        }

    # Auto-extract max_marks if not provided
    if max_marks is None:
        logger.info(f"Extracting max_marks for {question_part_label} from marking scheme...")
        max_marks = extract_max_marks_from_scheme(marking_scheme_image, question_part_label)

        if max_marks is None or max_marks == 0:
            logger.error(f"Failed to extract max_marks for {question_part_label}")
            return {
                'score': 0,
                'marks_awarded': 0.0,
                'feedback': 'Error: Could not determine maximum marks from marking scheme. Please contact your teacher.',
                'is_correct': False,
                'max_marks': 0
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

**Formatting** (the student sees this rendered in a web page - follow exactly):
- Wrap EVERY mathematical expression in single dollar delimiters, e.g. $\\frac{{3}}{{5}}$, $m = \\pm 6$
- This includes fractions, symbols and values standing alone in a sentence.
  LaTeX left outside $...$ displays to the student as raw code.
- Do NOT use \\( \\) or \\[ \\] delimiters. Only $...$ and $$...$$.
- Write plain prose sentences. Do NOT use Markdown: no **bold**, no headings,
  no bullet points, no numbered lists.

**Important:** Return ONLY a JSON object with these exact fields:
- "marks_awarded": number between 0 and {max_marks} (use decimals for partial credit, e.g., 3.5)
- "feedback": 2-4 plain sentences covering what the student got right (if
  anything), what was wrong or missing, the marking scheme criterion that
  applies, and what to do differently next time
- "is_correct": boolean (true if marks_awarded >= {max_marks * 0.95}, false otherwise)

Example response:
{{"marks_awarded": 7, "feedback": "You correctly identified that $m = \\pm 6$. The marking scheme awards full marks for showing all three steps: using $b^2 - 4ac = 0$, substituting the values, and solving for $m$. You gave the correct final answer without the working, so this earns high partial credit. Next time set out the substitution before solving.", "is_correct": false}}"""
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

        # Call the configured vision model
        response = _vision_completion(
            messages=[
                {
                    "role": "user",
                    "content": content
                }
            ],
            max_tokens=500,
            temperature=0.2,  # Low temperature for consistent grading
            response_format={"type": "json_object"}
        )

        # Parse the response
        raw_response = response.choices[0].message.content.strip()

        # Extract JSON from response with robust error handling
        import json
        import re

        # Try to parse JSON with multiple fallback methods
        try:
            result = json.loads(raw_response)
        except json.JSONDecodeError:
            # Fallback: try to extract JSON from markdown code blocks
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw_response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(1))
            else:
                # Last resort: try to find any JSON object (use greedy match for nested braces)
                json_match = re.search(r'\{.*\}', raw_response, re.DOTALL)
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
            'is_correct': is_correct and not (hint_used or solution_used),  # Not correct if used help
            'max_marks': max_marks
        }

    except Exception as e:
        logger.error(f"Error grading with vision API for {question_part_label}: {e}", exc_info=True)
        return {
            'score': 0,
            'marks_awarded': 0.0,
            'feedback': f'Grading error: {str(e)}. Please try again or contact support.',
            'is_correct': False,
            'max_marks': max_marks or 0
        }
