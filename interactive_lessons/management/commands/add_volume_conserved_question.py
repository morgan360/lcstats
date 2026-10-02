"""Add the test question for the Volume is Conserved QuickFlick and attach it.

One solid carried through the video's ideas, on fresh numbers:
  (a) volume of a cone, radius 6, height 8            96π
  (b) melted and recast as a cylinder of radius 4      height 6
  (c) that cylinder sunk in a tank of radius 8         water rises 1.5
(checked with fractions). Answers are whole multiples of π or plain numbers so
the grader checks them exactly.

Idempotent, keyed on topic slug, section name and question order like the other
add_* commands: Area & Volume's Medium section, after the Similar Solids test
question. Links itself to the QuickFlick only where one exists (production).
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from interactive_lessons.models import Question, QuestionPart, Section, Topic
from quickkicks.models import QuickKick

TOPIC_SLUG = "area-volume"
SECTION_NAME = "Medium"
ORDER = 5
QUICKFLICK_TITLE = "Volume is Conserved"

HINT = r"""Melting, recasting and sinking an object in water never change its volume. Write the volume before and the volume after, set them equal, and solve. When water rises in a container, the rise is a cylinder with the **container's** radius."""

PARTS = [
    {
        "label": "(a)",
        "prompt": r"""A solid metal cone has radius $6$ cm and height $8$ cm.

Find the volume of the cone, in terms of $\pi$.""",
        "answer": "96*pi",
        "expected_format": r"""In terms of $\pi$, number only (e.g., $48\pi$)""",
        "expected_type": "expression",
        "max_marks": 5,
        "solution": r"""**Step 1:** Use $V = \frac{1}{3}\pi r^2 h$ (*Formulae & Tables*, p. 10):

$$V = \frac{1}{3}\pi(6)^2(8) = \frac{1}{3}\pi(36)(8) = 96\pi$$

**Answer:** $96\pi$ cm³""",
    },
    {
        "label": "(b)",
        "prompt": r"""The cone is melted down and all of the metal is recast into a solid cylinder of radius $4$ cm.

Find the height of the cylinder.""",
        "answer": "6",
        "expected_format": "Number only, in cm (e.g., 5)",
        "expected_type": "numeric",
        "max_marks": 10,
        "solution": r"""**Step 1:** Volume before = volume after:

$$\pi(4)^2 h = 96\pi$$

**Step 2:**

$$16\pi h = 96\pi \quad\Rightarrow\quad h = \frac{96}{16} = 6$$

**Answer:** $6$ cm""",
    },
    {
        "label": "(c)",
        "prompt": r"""The cylinder is dropped into a cylindrical tank of radius $8$ cm, which contains some water. The cylinder sinks and is completely covered.

Find the rise in the water level.""",
        "answer": "1.5",
        "expected_format": "Number only, in cm (e.g., 2.5)",
        "expected_type": "numeric",
        "max_marks": 10,
        "solution": r"""**Step 1:** The water rises by exactly the volume of the cylinder, $96\pi$ cm³.

**Step 2:** The rise is a cylinder with the **tank's** radius, $8$ cm (not the radius of the object):

$$\pi(8)^2 d = 96\pi$$

$$64\pi d = 96\pi \quad\Rightarrow\quad d = \frac{96}{64} = 1.5$$

**Answer:** $1.5$ cm""",
    },
]


class Command(BaseCommand):
    help = "Add the Volume is Conserved QuickFlick test question and attach it to the QuickFlick"

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
