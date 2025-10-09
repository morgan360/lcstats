import re
import os
from django.utils.text import slugify
from pylatexenc.latex2text import LatexNodes2Text
from interactive_lessons.models import Topic, Question


def latex_to_html(latex_text):
    """Convert LaTeX to plain readable text."""
    return LatexNodes2Text().latex_to_text(latex_text).strip()


def import_from_tex(filepath, topic_name):
    """Import questions and answers from a LaTeX file into Topic and Question models."""
    with open(filepath, "r") as f:
        tex = f.read()

    # Convert LaTeX image includes into HTML img tags
    tex = re.sub(
        r"\\includegraphics(?:\[.*?\])?{(.*?)}",
        lambda m: f'<img src="/static/interactive_lessons/{os.path.basename(m.group(1))}" '
                  f'class="mx-auto my-4 rounded shadow" alt="{m.group(1)}"/>',
        tex
    )

    # Get or create topic
    topic, _ = Topic.objects.get_or_create(name=topic_name)
    topic.slug = slugify(topic_name)
    topic.save()

    # Split document into sections
    sections = re.split(r"\\section\{(.*?)\}", tex)
    order_counter = 0

    for i in range(1, len(sections), 2):
        section_name = sections[i].strip()
        section_body = sections[i + 1]

        # Find all questions inside examplebox blocks
        questions = re.findall(r"\\begin{examplebox}(.*?)\\end{examplebox}", section_body, re.S)

        # Match answer blocks
        answer_blocks = re.findall(
            r"\\textbf\{Answer to Question\s+(\d+):\}.*?\\\\(.*?)(?=(?:\\textbf\{Answer to Question|\Z))",
            section_body, re.S
        )
        answers_by_index = {int(num): block for num, block in answer_blocks}

        for idx, q in enumerate(questions, start=1):
            q_text = latex_to_html(q)
            ans_block = answers_by_index.get(idx, "")
            ans_text = latex_to_html(ans_block)

            # Extract Hint (if exists)
            hint_match = re.search(r"\\textbf\{Hint:\}\s*\\\\?\s*(.*?)(?=\\textbf\{|$)", ans_block, re.S)
            hint_text = latex_to_html(hint_match.group(1)) if hint_match else None

            # Extract Explanation or Interpretation (for full solution)
            solution_match = re.search(
                r"\\textbf\{(Explanation|Interpretation):\}\s*\\\\?\s*(.*)", ans_block, re.S
            )
            solution_text = latex_to_html(solution_match.group(2)) if solution_match else None

            order_counter += 1

            # Create or update question
            Question.objects.update_or_create(
                topic=topic,
                order=order_counter,
                defaults={
                    "section": section_name,
                    "text": q_text,
                    "answer": ans_text,
                    "hint": hint_text,
                    "solution": solution_text,
                }
            )

    print(f"✅ Imported {order_counter} questions for topic '{topic_name}'")
