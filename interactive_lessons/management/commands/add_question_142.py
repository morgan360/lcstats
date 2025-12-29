"""
Management command to add Question 142: Binomial Distribution - Evan Ferguson Scoring
"""
from django.core.management.base import BaseCommand
from interactive_lessons.models import Topic, Question, QuestionPart


class Command(BaseCommand):
    help = "Add Question 142: Binomial Distribution - Evan Ferguson Scoring"

    def handle(self, *args, **options):
        # Get Probability topic
        topic = Topic.objects.get(name="Probability")

        # Create Question 142
        question = Question.objects.create(
            topic=topic,
            order=44,
            section="Binomial Distribution",
            hint="""This is a **Binomial Distribution** problem.

**Given:**
- $n = 16$ (total games)
- $r = 9$ (number of games we want him to score in)
- $p = 0.42$ (probability of scoring in each game)

**Formula:**
$$P(X = r) = \\binom{n}{r} p^r (1-p)^{n-r}$$

**Note:** "Exactly any 9" means **exactly 9 games**, not "at least 9".""",
        )

        # Single part - Find probability of exactly 9 out of 16
        QuestionPart.objects.create(
            question=question,
            label="",
            order=1,
            prompt="""Evan Ferguson scores in 42% of the games that he plays in.

If he plays in 16 games for his club, what is the probability, to four decimal places, that he scores in exactly any 9 of them?""",
            answer="0.1027",
            expected_format="Give your answer as a decimal rounded to 4 decimal places.",
            expected_type="numeric",
            max_marks=10,
            solution="""
**Step 1: Identify the distribution**

This is a **Binomial Distribution** problem with:
- $n = 16$ (total number of games)
- $r = 9$ (number of games we want him to score in)
- $p = 0.42$ (probability of scoring in a game)
- $q = 1 - p = 0.58$ (probability of not scoring in a game)

**Step 2: Apply the Binomial Probability Formula**

$$P(X = r) = \\binom{n}{r} p^r (1-p)^{n-r}$$

$$P(X = 9) = \\binom{16}{9} (0.42)^9 (0.58)^{16-9}$$

$$P(X = 9) = \\binom{16}{9} (0.42)^9 (0.58)^7$$

**Step 3: Calculate the combination**

$$\\binom{16}{9} = \\frac{16!}{9!(16-9)!} = \\frac{16!}{9! \\cdot 7!}$$

$$\\binom{16}{9} = \\frac{16 \\times 15 \\times 14 \\times 13 \\times 12 \\times 11 \\times 10}{7 \\times 6 \\times 5 \\times 4 \\times 3 \\times 2 \\times 1}$$

$$\\binom{16}{9} = \\frac{57657600}{5040} = 11440$$

**Step 4: Calculate the probability (use calculator for accuracy)**

$$P(X = 9) = 11440 \\times (0.42)^9 \\times (0.58)^7$$

Using a calculator with full precision:
- $\\binom{16}{9} = 11440$
- $(0.42)^9 = 0.00016983326...$
- $(0.58)^7 = 0.02211336...$
- $11440 \\times 0.00016983326... \\times 0.02211336... = 0.102734...$

$$P(X = 9) = 0.1027$$

**Answer: 0.1027**

**Interpretation:** There is approximately a 10.27% chance that Evan Ferguson scores in exactly 9 out of 16 games.

**Calculator Note:** On a calculator with binomial distribution functions, you can use:
- binompdf(16, 0.42, 9) ≈ 0.1027

**Important:** When dealing with binomial probabilities, it's essential to use a calculator and keep full precision throughout the calculation to avoid rounding errors that accumulate.

**Note on "Exactly any 9":** This phrasing means exactly 9 games (any combination of 9 from the 16), not at least 9. The binomial coefficient $\\binom{16}{9}$ accounts for all the different ways to choose which 9 games he scores in.
            """,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Created Question {question.id}: Probability - Binomial Distribution (Evan Ferguson Scoring)\n"
                f"   Order: {question.order}\n"
                f"   Section: {question.section}\n"
                f"   Parts: {question.parts.count()}\n"
            )
        )
