"""Add the test question for the Tree Diagrams QuickFlick and attach it.

The video's three ideas, one part each, on a fresh example so the question tests
the method rather than memory of the video's numbers:
  (a) without replacement the second-stage fraction changes   1/3
  (b) multiply along a path                                   2/15
  (c) add the paths that give the event                       8/15
(answers checked by enumerating all 90 ordered draws).

Idempotent, keyed on topic slug, section name and question order like the other
add_* commands, since ids differ between local and production. The QuickFlick
lives only on production; where it is missing the question is still written and
the link is reported as skipped.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from interactive_lessons.models import Question, QuestionPart, Section, Topic
from quickkicks.models import QuickKick

TOPIC_SLUG = "probability"
SECTION_NAME = "Tree Diagrams"
ORDER = 36
QUICKFLICK_TITLE = "Tree Diagrams"

STEM = "A box contains $4$ green sweets and $6$ yellow sweets. Two sweets are taken at random, one after the other, without replacement."
FRACTION_FORMAT = r"""Fraction in simplest form (e.g., $\frac{3}{7}$)"""

HINT = r"""Draw the tree: first sweet, then second sweet. Without replacement, the second-stage fractions are out of $9$, and the numerators depend on what was taken first. **Multiply** along a path for one outcome; **add** the paths that give the event you want."""

PARTS = [
    {
        "label": "(a)",
        "prompt": STEM + r"""

The first sweet taken is green. What is the probability that the second sweet is also green?""",
        "answer": "1/3",
        "max_marks": 5,
        "solution": r"""**Step 1:** After one green sweet is taken, the box holds $9$ sweets, of which $3$ are green.

**Step 2:**

$$P(\text{2nd green} \mid \text{1st green}) = \frac{3}{9} = \frac{1}{3}$$

This is the fraction on the second-stage branch after G. Without replacement, both its top and its bottom have dropped by one.

**Answer:** $\frac{1}{3}$""",
    },
    {
        "label": "(b)",
        "prompt": r"""Find the probability that both sweets are green.""",
        "answer": "2/15",
        "max_marks": 5,
        "solution": r"""**Step 1:** Follow the G then G path and multiply along it:

$$P(GG) = \frac{4}{10} \times \frac{3}{9} = \frac{12}{90}$$

**Step 2:** Simplify:

$$\frac{12}{90} = \frac{2}{15}$$

**Answer:** $\frac{2}{15}$""",
    },
    {
        "label": "(c)",
        "prompt": r"""Find the probability that one sweet of each colour is taken.""",
        "answer": "8/15",
        "max_marks": 10,
        "solution": r"""**Step 1:** Two paths give one of each colour: G then Y, and Y then G.

**Step 2:** Multiply along each path:

$$P(GY) = \frac{4}{10} \times \frac{6}{9} = \frac{24}{90} \qquad P(YG) = \frac{6}{10} \times \frac{4}{9} = \frac{24}{90}$$

**Step 3:** Add the paths:

$$P(\text{one of each}) = \frac{24}{90} + \frac{24}{90} = \frac{48}{90} = \frac{8}{15}$$

*(Check: $P(GG) + P(YY) = \frac{12}{90} + \frac{30}{90} = \frac{42}{90}$, and $\frac{42}{90} + \frac{48}{90} = 1$.)*

**Answer:** $\frac{8}{15}$""",
    },
]


class Command(BaseCommand):
    help = "Add the Tree Diagrams QuickFlick test question and attach it to the QuickFlick"

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
                        "expected_format": FRACTION_FORMAT,
                        "solution": part["solution"],
                        "expected_type": "numeric",
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
