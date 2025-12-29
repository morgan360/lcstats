"""
Management command to add Question 135: Lottery Probability - Combinations
"""
from django.core.management.base import BaseCommand
from interactive_lessons.models import Topic, Question, QuestionPart


class Command(BaseCommand):
    help = "Add Question 135: Lottery Probability - Combinations"

    def handle(self, *args, **options):
        # Get Probability topic
        topic = Topic.objects.get(name="Probability")

        # Create Question 135
        question = Question.objects.create(
            topic=topic,
            order=39,
            section="Combinations and Probability",
            hint="""Calculate the total number of ways to choose 3 numbers from 24 using $\\binom{24}{3}$.

For part (i): There's only 1 way to match all 3 numbers.

For part (ii): You need to match exactly 2 of the 3 winning numbers, and have 1 non-winning number.""",
        )

        # Part (i) - Win €800
        QuestionPart.objects.create(
            question=question,
            label="(i)",
            order=1,
            prompt="""Liam Mellows Hurling Club have a weekly lotto. To play you must choose 3 numbers from 1 – 24.

- You win €800 if you match all three numbers.
- You win €75 if you match two of the three numbers.

What is the probability someone who purchases a ticket will:

**(i)** Win the €800?""",
            answer="1/2024",
            expected_format="Give your answer as a fraction in simplest form.",
            expected_type="exact",
            max_marks=5,
            solution="""
**Step 1: Calculate total possible outcomes**

Total ways to choose 3 numbers from 24:
$$\\binom{24}{3} = \\frac{24!}{3!(24-3)!} = \\frac{24 \\times 23 \\times 22}{3 \\times 2 \\times 1} = \\frac{12144}{6} = 2024$$

**Step 2: Calculate favorable outcomes**

To win €800, you must match all 3 winning numbers.

Number of ways to match all 3 numbers = 1 (there's only one winning combination)

**Step 3: Calculate probability**

$$P(\\text{win €800}) = \\frac{\\text{favorable outcomes}}{\\text{total outcomes}} = \\frac{1}{2024}$$

**Answer: $\\frac{1}{2024}$**
            """,
        )

        # Part (ii) - Win €75
        QuestionPart.objects.create(
            question=question,
            label="(ii)",
            order=2,
            prompt="**(ii)** Win the €75?",
            answer="63/2024",
            expected_format="Give your answer as a fraction in simplest form.",
            expected_type="exact",
            max_marks=5,
            solution="""
**Step 1: Total possible outcomes**

From part (i), we know:
$$\\binom{24}{3} = 2024$$

**Step 2: Calculate favorable outcomes**

To win €75, you must match exactly 2 of the 3 winning numbers (and have 1 non-winning number).

- Ways to choose 2 numbers from the 3 winning numbers: $\\binom{3}{2} = 3$
- Ways to choose 1 number from the 21 non-winning numbers: $\\binom{21}{1} = 21$

Total favorable outcomes:
$$\\binom{3}{2} \\times \\binom{21}{1} = 3 \\times 21 = 63$$

**Step 3: Calculate probability**

$$P(\\text{win €75}) = \\frac{63}{2024}$$

**Answer: $\\frac{63}{2024}$**

(This fraction is already in simplest form since gcd(63, 2024) = 1)
            """,
        )

        # Part (iii) - Fair game?
        QuestionPart.objects.create(
            question=question,
            label="(iii)",
            order=3,
            prompt="**(iii)** The cost of a ticket in the Liam Mellows Hurling Club lotto is €3. Is this a fair game for the player?",
            answer="No",
            expected_format="Answer 'Yes' or 'No' and justify your answer by calculating the expected value.",
            expected_type="manual",
            max_marks=5,
            solution="""
A game is fair if the **expected value** equals the cost to play.

**Step 1: Calculate Expected Value**

Expected Value = (Probability of winning €800 × €800) + (Probability of winning €75 × €75) + (Probability of winning nothing × €0)

From parts (i) and (ii):
- $P(\\text{win €800}) = \\frac{1}{2024}$
- $P(\\text{win €75}) = \\frac{63}{2024}$
- $P(\\text{win nothing}) = 1 - \\frac{1}{2024} - \\frac{63}{2024} = \\frac{1960}{2024}$

$$E(X) = \\frac{1}{2024} \\times 800 + \\frac{63}{2024} \\times 75 + \\frac{1960}{2024} \\times 0$$

$$E(X) = \\frac{800}{2024} + \\frac{4725}{2024}$$

$$E(X) = \\frac{5525}{2024}$$

$$E(X) \\approx €2.73$$

**Step 2: Compare to cost**

- Cost to play: €3
- Expected value: €2.73

Since the expected value (€2.73) is **less than** the cost to play (€3), the player expects to lose money on average.

**Answer: No, this is not a fair game for the player.**

The player loses approximately €0.27 per ticket on average. This is favorable to the club (house advantage).
            """,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Created Question {question.id}: Probability - Lottery (Combinations)\n"
                f"   Order: {question.order}\n"
                f"   Section: {question.section}\n"
                f"   Parts: {question.parts.count()}\n"
            )
        )
