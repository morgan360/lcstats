"""
Management command to add Question 143: Binomial Distribution - Rain in Ireland
"""
from django.core.management.base import BaseCommand
from interactive_lessons.models import Topic, Question, QuestionPart


class Command(BaseCommand):
    help = "Add Question 143: Binomial Distribution - Rain in Ireland"

    def handle(self, *args, **options):
        # Get Probability topic
        topic = Topic.objects.get(name="Probability")

        # Create Question 143
        question = Question.objects.create(
            topic=topic,
            order=45,
            section="Binomial Distribution",
            hint="""This is a **Binomial Distribution** problem.

**Given:**
- $n = 14$ (total days)
- $r = 7$ (number of days we want it to rain - "exactly half of 14")
- $p = 0.55$ (probability of rain on any given day)

**Formula:**
$$P(X = r) = \\binom{n}{r} p^r (1-p)^{n-r}$$

**Important:** Use a calculator with full precision to get the answer to 6 decimal places.""",
        )

        # Single part - Find probability of exactly 7 rainy days out of 14
        QuestionPart.objects.create(
            question=question,
            label="",
            order=1,
            prompt="""In Ireland, the chance of rain on any given day is 55%. Over the next fourteen days, find the probability, correct to six decimal places, that it rains on exactly half of those days?""",
            answer="0.195242",
            expected_format="Give your answer as a decimal rounded to 6 decimal places.",
            expected_type="numeric",
            max_marks=10,
            solution="""
**Step 1: Identify the distribution**

This is a **Binomial Distribution** problem with:
- $n = 14$ (total number of days)
- $r = 7$ (number of rainy days we want - exactly half of 14)
- $p = 0.55$ (probability of rain on any given day)
- $q = 1 - p = 0.45$ (probability of no rain on any given day)

**Step 2: Apply the Binomial Probability Formula**

$$P(X = r) = \\binom{n}{r} p^r (1-p)^{n-r}$$

$$P(X = 7) = \\binom{14}{7} (0.55)^7 (0.45)^{14-7}$$

$$P(X = 7) = \\binom{14}{7} (0.55)^7 (0.45)^7$$

**Step 3: Calculate the combination**

$$\\binom{14}{7} = \\frac{14!}{7!(14-7)!} = \\frac{14!}{7! \\cdot 7!}$$

$$\\binom{14}{7} = \\frac{14 \\times 13 \\times 12 \\times 11 \\times 10 \\times 9 \\times 8}{7 \\times 6 \\times 5 \\times 4 \\times 3 \\times 2 \\times 1}$$

$$\\binom{14}{7} = \\frac{17297280}{5040} = 3432$$

**Step 4: Calculate the probability (use calculator for full precision)**

$$P(X = 7) = 3432 \\times (0.55)^7 \\times (0.45)^7$$

Using a calculator with full precision:
- $\\binom{14}{7} = 3432$
- $(0.55)^7 = 0.0152400...$
- $(0.45)^7 = 0.00373669...$
- $3432 \\times 0.0152400... \\times 0.00373669... = 0.195242...$

$$P(X = 7) = 0.195242$$

**Answer: 0.195242**

**Interpretation:** There is approximately a 19.52% chance that it will rain on exactly 7 out of the next 14 days in Ireland.

**Calculator Note:** On a calculator with binomial distribution functions, you can use:
- binompdf(14, 0.55, 7) ≈ 0.195242

**Note:** This makes intuitive sense - with a 55% chance of rain each day, the most likely outcome is around 7-8 rainy days, so this probability (about 19.5%) is relatively high compared to other specific outcomes.
            """,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Created Question {question.id}: Probability - Binomial Distribution (Rain in Ireland)\n"
                f"   Order: {question.order}\n"
                f"   Section: {question.section}\n"
                f"   Parts: {question.parts.count()}\n"
            )
        )
