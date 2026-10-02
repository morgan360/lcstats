"""Add the test question for the Similar Solids QuickFlick and attach it.

The video's rule on fresh numbers -- two similar cylinders, radii 4 and 6:
  (a) the scale factor k                       3/2
  (b) volume scales by k³:   48π  -> 162π
  (c) area scales by k²:     40π  ->  90π
(checked with fractions). Answers are whole multiples of π so the grader checks
them exactly, numerically and algebraically.

Idempotent, keyed on topic slug, section name and question order like the other
add_* commands. It sits in Area & Volume's Medium section, after the three from
add_area_volume_questions. The QuickFlick lives only on production; where it is
missing the question is still written and the link is reported as skipped.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from interactive_lessons.models import Question, QuestionPart, Section, Topic
from quickkicks.models import QuickKick

TOPIC_SLUG = "area-volume"
SECTION_NAME = "Medium"
ORDER = 4
QUICKFLICK_TITLE = "Similar Solids: k, k², k³"

PI_FORMAT = r"""In terms of $\pi$, number only (e.g., $48\pi$)"""

HINT = r"""For **similar** solids, every length is multiplied by the same scale factor $k$. Then every area is multiplied by $k^2$ and every volume by $k^3$. Find $k$ from a pair of matching lengths first."""

STEM = r"""Two cylinders are similar. The smaller has radius $4$ cm and the larger has radius $6$ cm."""

PARTS = [
    {
        "label": "(a)",
        "prompt": STEM + r"""

Find the scale factor $k$ from the smaller cylinder to the larger.""",
        "answer": "1.5",
        "expected_format": r"""Number, as a fraction or decimal (e.g., $\frac{5}{4}$ or $1.25$)""",
        "expected_type": "numeric",
        "max_marks": 5,
        "solution": r"""**Step 1:** The radii are matching lengths, so their ratio is the scale factor:

$$k = \frac{6}{4} = \frac{3}{2}$$

**Answer:** $k = \frac{3}{2}$ (or $1.5$)""",
    },
    {
        "label": "(b)",
        "prompt": r"""The volume of the smaller cylinder is $48\pi$ cm³.

Find the volume of the larger cylinder, in terms of $\pi$.""",
        "answer": "162*pi",
        "expected_format": PI_FORMAT,
        "expected_type": "expression",
        "max_marks": 10,
        "solution": r"""**Step 1:** Volumes of similar solids scale by $k^3$:

$$k^3 = \left(\frac{3}{2}\right)^3 = \frac{27}{8}$$

**Step 2:**

$$V = 48\pi \times \frac{27}{8} = 6\pi \times 27 = 162\pi$$

*(Check with the formula: the smaller cylinder has $\pi(4)^2 h = 48\pi$, so $h = 3$; the larger has height $3 \times \frac{3}{2} = 4.5$ and volume $\pi(6)^2(4.5) = 162\pi$.)*

**Answer:** $162\pi$ cm³""",
    },
    {
        "label": "(c)",
        "prompt": r"""The curved surface area of the smaller cylinder is $40\pi$ cm².

Find the curved surface area of the larger cylinder, in terms of $\pi$.""",
        "answer": "90*pi",
        "expected_format": PI_FORMAT,
        "expected_type": "expression",
        "max_marks": 10,
        "solution": r"""**Step 1:** Areas of similar solids scale by $k^2$, not $k$ or $k^3$:

$$k^2 = \left(\frac{3}{2}\right)^2 = \frac{9}{4}$$

**Step 2:**

$$A = 40\pi \times \frac{9}{4} = 10\pi \times 9 = 90\pi$$

**Answer:** $90\pi$ cm²""",
    },
]


class Command(BaseCommand):
    help = "Add the Similar Solids QuickFlick test question and attach it to the QuickFlick"

    def handle(self, *args, **options):
        with transaction.atomic():
            topic = Topic.objects.get(slug=TOPIC_SLUG)
            section, _ = Section.objects.get_or_create(topic=topic, name=SECTION_NAME)

            question, made = Question.objects.update_or_create(
                topic=topic,
                section=section,
                order=ORDER,
                defaults={
                    "hint": HINT,
                    "solution": None,
                    "is_copyrighted": True,
                    "is_exam_question": False,
                    # The QuickFlick admin only offers questions with this flag.
                    "is_quickkick_suitable": True,
                },
            )
            self.stdout.write(f'{"Created" if made else "Updated"} question {question.id} '
                              f'({topic.name} / {section.name} / order {ORDER})')

            for order, part in enumerate(PARTS):
                QuestionPart.objects.update_or_create(
                    question=question,
                    label=part["label"],
                    defaults={
                        "prompt": part["prompt"],
                        "answer": part["answer"],
                        "expected_format": part["expected_format"],
                        "solution": part["solution"],
                        "expected_type": part["expected_type"],
                        "max_marks": part["max_marks"],
                        "order": order,
                        "solution_unlock_after_attempts": 2,
                        "scale": None,
                        "is_quickkick_suitable": True,
                    },
                )

            flick = QuickKick.objects.filter(topic=topic, title=QUICKFLICK_TITLE).first()
            if flick is None:
                self.stdout.write(self.style.WARNING(
                    f'  no "{QUICKFLICK_TITLE}" QuickFlick here - question written, link skipped'
                ))
            else:
                flick.question = question
                flick.save(update_fields=["question", "updated_at"])
                self.stdout.write(f"  attached to QuickFlick {flick.id}")

        self.stdout.write(self.style.SUCCESS(f"Wrote 1 question and {len(PARTS)} parts."))
