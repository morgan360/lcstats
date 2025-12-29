"""
Management command to add Question 144: Binomial Distribution - Leaving Certificate Exams
"""
from django.core.management.base import BaseCommand
from interactive_lessons.models import Topic, Question, QuestionPart


class Command(BaseCommand):
    help = "Add Question 144: Binomial Distribution - Leaving Certificate Exams"

    def handle(self, *args, **options):
        # Get Probability topic
        topic = Topic.objects.get(name="Probability")

        # Create Question 144
        question = Question.objects.create(
            topic=topic,
            order=46,
            section="Binomial Distribution",
            hint="""This is a **Binomial Distribution** problem with **"at least"** language.

**Given:**
- $n = 9$ (total exams)
- $p = 0.88$ (probability of passing any exam)
- Find: $P(X \\geq 8)$ = "at least 8"

**Important:** "At least 8" means 8 **or more**, so:
$$P(X \\geq 8) = P(X = 8) + P(X = 9)$$

Use the binomial formula for each:
$$P(X = r) = \\binom{n}{r} p^r (1-p)^{n-r}$$

Calculate both probabilities and add them together.""",
        )

        # Single part - Find probability of passing at least 8 out of 9
        QuestionPart.objects.create(
            question=question,
            label="",
            order=1,
            prompt="""The probability that Laura will pass any of her Leaving Certificate exams is 0.88. She sits 9 exams for her Leaving Certificate. What is the probability, correct to six decimal places, that she passes at least 8 of them?""",
            answer="0.704884",
            expected_format="Give your answer as a decimal rounded to 6 decimal places.",
            expected_type="numeric",
            max_marks=10,
            solution="""
**Step 1: Identify the distribution and interpret "at least"**

This is a **Binomial Distribution** problem with:
- $n = 9$ (total number of exams)
- $p = 0.88$ (probability of passing any exam)
- $q = 1 - p = 0.12$ (probability of failing any exam)

**"At least 8"** means 8 or 9, so:
$$P(X \\geq 8) = P(X = 8) + P(X = 9)$$

**Step 2: Calculate P(X = 8)**

$$P(X = 8) = \\binom{9}{8} (0.88)^8 (0.12)^{9-8}$$

$$P(X = 8) = \\binom{9}{8} (0.88)^8 (0.12)^1$$

Calculate:
- $\\binom{9}{8} = \\frac{9!}{8! \\cdot 1!} = 9$
- $(0.88)^8 = 0.3596588...$
- $(0.12)^1 = 0.12$
- $P(X = 8) = 9 \\times 0.3596588... \\times 0.12 = 0.388391...$

**Step 3: Calculate P(X = 9)**

$$P(X = 9) = \\binom{9}{9} (0.88)^9 (0.12)^{9-9}$$

$$P(X = 9) = \\binom{9}{9} (0.88)^9 (0.12)^0$$

Calculate:
- $\\binom{9}{9} = 1$
- $(0.88)^9 = 0.3164977...$
- $(0.12)^0 = 1$
- $P(X = 9) = 1 \\times 0.3164977... \\times 1 = 0.316498...$

**Step 4: Add the probabilities**

$$P(X \\geq 8) = P(X = 8) + P(X = 9)$$

$$P(X \\geq 8) = 0.388391... + 0.316498...$$

$$P(X \\geq 8) = 0.704884$$

**Answer: 0.704884**

**Interpretation:** There is approximately a 70.49% chance that Laura will pass at least 8 out of 9 Leaving Certificate exams.

**Calculator Note:** On a calculator with binomial distribution functions, you can use:
- binomcdf(9, 0.88, 9) - binomcdf(9, 0.88, 7) ≈ 0.704884
- OR: binompdf(9, 0.88, 8) + binompdf(9, 0.88, 9) ≈ 0.704884

**Key Point:** Always check if the question asks for "exactly", "at least", or "at most":
- **Exactly r:** $P(X = r)$ (single value)
- **At least r:** $P(X \\geq r) = P(X = r) + P(X = r+1) + ... + P(X = n)$ (sum from r to n)
- **At most r:** $P(X \\leq r) = P(X = 0) + P(X = 1) + ... + P(X = r)$ (sum from 0 to r)
            """,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Created Question {question.id}: Probability - Binomial Distribution (Leaving Cert Exams)\n"
                f"   Order: {question.order}\n"
                f"   Section: {question.section}\n"
                f"   Parts: {question.parts.count()}\n"
            )
        )
