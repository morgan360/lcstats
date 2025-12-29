"""
Management command to add Question 141: Binomial Distribution - Penalty Scoring
"""
from django.core.management.base import BaseCommand
from interactive_lessons.models import Topic, Question, QuestionPart


class Command(BaseCommand):
    help = "Add Question 141: Binomial Distribution - Penalty Scoring"

    def handle(self, *args, **options):
        # Get Probability topic
        topic = Topic.objects.get(name="Probability")

        # Create Question 141
        question = Question.objects.create(
            topic=topic,
            order=43,
            section="Bernoulli Trials",
            hint="""This is a **Binomial Distribution** problem.

**Given:**
- $n = 9$ (total penalties)
- $r = 6$ (number of penalties we want him to score)
- $p = 0.85$ (probability of scoring each penalty)

**Formula:**
$$P(X = r) = \\binom{n}{r} p^r (1-p)^{n-r}$$

**Note:** "Any 6 out of 9" means **exactly 6**, not "at least 6".""",
        )

        # Single part - Find probability of exactly 6 out of 9
        QuestionPart.objects.create(
            question=question,
            label="",
            order=1,
            prompt="""The probability of Bruno Fernandes scoring a penalty is 0.85. Find the probability, to 5 decimal places, that he scores any 6 out of 9 penalties in a season.""",
            answer="0.10676",
            expected_format="Give your answer as a decimal rounded to 5 decimal places.",
            expected_type="numeric",
            max_marks=10,
            solution="""
**Step 1: Identify the distribution**

This is a **Binomial Distribution** problem with:
- $n = 9$ (total number of penalties)
- $r = 6$ (number we want him to score)
- $p = 0.85$ (probability of scoring)
- $q = 1 - p = 0.15$ (probability of missing)

**Step 2: Apply the Binomial Probability Formula**

$$P(X = r) = \\binom{n}{r} p^r (1-p)^{n-r}$$

$$P(X = 6) = \\binom{9}{6} (0.85)^6 (0.15)^{9-6}$$

$$P(X = 6) = \\binom{9}{6} (0.85)^6 (0.15)^3$$

**Step 3: Calculate the combination**

$$\\binom{9}{6} = \\frac{9!}{6!(9-6)!} = \\frac{9!}{6! \\cdot 3!}$$

$$\\binom{9}{6} = \\frac{9 \\times 8 \\times 7}{3 \\times 2 \\times 1} = \\frac{504}{6} = 84$$

**Step 4: Calculate the probability**

$$P(X = 6) = 84 \\times (0.85)^6 \\times (0.15)^3$$

Calculate each part:
- $(0.85)^6 = 0.377149...$
- $(0.15)^3 = 0.003375$
- $84 \\times 0.377149... \\times 0.003375 = 0.10676...$

$$P(X = 6) = 0.10676$$

**Answer: 0.10676**

**Interpretation:** There is approximately a 10.68% chance that Bruno Fernandes scores exactly 6 out of 9 penalties in a season.

**Calculator Note:** On a calculator with binomial distribution functions, you can use:
- binompdf(9, 0.85, 6) ≈ 0.10676

**Note:** If the question asked for "at least 6 out of 9", you would need to calculate:
$$P(X \\geq 6) = P(X=6) + P(X=7) + P(X=8) + P(X=9)$$
But since it asks for "any 6", we interpret this as **exactly 6**.
            """,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Created Question {question.id}: Probability - Binomial Distribution (Penalty Scoring)\n"
                f"   Order: {question.order}\n"
                f"   Section: {question.section}\n"
                f"   Parts: {question.parts.count()}\n"
            )
        )