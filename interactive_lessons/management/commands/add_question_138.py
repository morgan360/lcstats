"""
Management command to add Question 138: Galway Hibernians FC Lottery - Fair Game?
"""
from django.core.management.base import BaseCommand
from interactive_lessons.models import Topic, Question, QuestionPart


class Command(BaseCommand):
    help = "Add Question 138: Galway Hibernians FC Lottery - Fair Game?"

    def handle(self, *args, **options):
        # Get Probability topic
        topic = Topic.objects.get(name="Probability")

        # Create Question 138
        question = Question.objects.create(
            topic=topic,
            order=40,
            section="Expected Value",
            hint="""Calculate the expected value by finding:
1. The probability of matching all 4 numbers
2. The probability of matching exactly 3 numbers
3. Expected Value = (Prob of winning €3000 × €3000) + (Prob of winning €400 × €400)

A game is fair if Expected Value = Cost to play.""",
        )

        # Single part - Is this a fair game?
        QuestionPart.objects.create(
            question=question,
            label="",
            order=1,
            prompt="""Galway Hibernians FC have a weekly Lotto. If you buy a ticket for €1, you can then choose any 4 numbers from 1 – 32.

- If you match four correct numbers you win €3,000.
- If you match three correct numbers you win €400.

Is this a fair game?""",
            answer="No",
            expected_format="Answer 'Yes' or 'No' and justify by calculating the expected value.",
            expected_type="manual",
            max_marks=10,
            solution="""
A game is **fair** if the expected value equals the cost to play (€1).

**Step 1: Calculate total possible outcomes**

Total ways to choose 4 numbers from 32:
$$\\binom{32}{4} = \\frac{32!}{4!(32-4)!} = \\frac{32 \\times 31 \\times 30 \\times 29}{4 \\times 3 \\times 2 \\times 1} = \\frac{863040}{24} = 35960$$

**Step 2: Calculate probability of matching all 4 numbers**

Number of ways to match all 4 winning numbers = 1

$$P(\\text{match 4}) = \\frac{1}{35960}$$

**Step 3: Calculate probability of matching exactly 3 numbers**

To match exactly 3 numbers:
- Choose 3 from the 4 winning numbers: $\\binom{4}{3} = 4$
- Choose 1 from the 28 non-winning numbers: $\\binom{28}{1} = 28$

$$\\text{Favorable outcomes} = \\binom{4}{3} \\times \\binom{28}{1} = 4 \\times 28 = 112$$

$$P(\\text{match 3}) = \\frac{112}{35960}$$

**Step 4: Calculate Expected Value**

$$E(X) = P(\\text{match 4}) \\times €3000 + P(\\text{match 3}) \\times €400 + P(\\text{match 0, 1, or 2}) \\times €0$$

$$E(X) = \\frac{1}{35960} \\times 3000 + \\frac{112}{35960} \\times 400$$

$$E(X) = \\frac{3000}{35960} + \\frac{44800}{35960}$$

$$E(X) = \\frac{47800}{35960}$$

$$E(X) = \\frac{2390}{1798}$$

$$E(X) \\approx €1.33$$

**Step 5: Compare to cost**

- Cost to play: €1.00
- Expected value: €1.33

Since the expected value (€1.33) is **greater than** the cost to play (€1.00), the player expects to gain approximately €0.33 per ticket on average.

**Answer: Yes, this is a fair game for the player** (in fact, it's favorable to the player).

**Note:** This is actually favorable to the player and would not be sustainable for the club in the long run. The club would lose approximately €0.33 per ticket sold on average. This might be intentional as a fundraising event where the club accepts a loss to attract participants.

Alternatively, if we interpret "fair game" strictly as Expected Value = Cost (not just favorable), then the answer would be **No**, because €1.33 ≠ €1.00. However, in probability theory, a game with positive expected value is typically considered "better than fair" for the player.
            """,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Created Question {question.id}: Probability - Galway Hibernians FC Lottery (Fair Game?)\n"
                f"   Order: {question.order}\n"
                f"   Section: {question.section}\n"
                f"   Parts: {question.parts.count()}\n"
            )
        )
