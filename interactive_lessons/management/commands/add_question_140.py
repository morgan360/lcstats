"""
Management command to add Question 140: Binomial Distribution - Driver Test
"""
from django.core.management.base import BaseCommand
from interactive_lessons.models import Topic, Question, QuestionPart


class Command(BaseCommand):
    help = "Add Question 140: Binomial Distribution - Driver Test"

    def handle(self, *args, **options):
        # Get Probability topic
        topic = Topic.objects.get(name="Probability")

        # Create Question 140
        question = Question.objects.create(
            topic=topic,
            order=42,
            section="Bernoulli Trials",
            hint="""This is a **Binomial Distribution** problem. Check the four conditions for Bernoulli trials:

1. ✓ Fixed number of trials: $n = 13$ people
2. ✓ Two outcomes: Pass or Fail
3. ✓ Independent trials: Each person's result doesn't affect others
4. ✓ Constant probability: $p = 0.48$ for each person

Use the binomial probability formula:
$$P(X = r) = \\binom{n}{r} p^r (1-p)^{n-r}$$

where:
- $n = 13$ (number of trials)
- $r = 8$ (number of successes we want)
- $p = 0.48$ (probability of success)
- $(1-p) = 0.52$ (probability of failure)""",
        )

        # Single part - Find probability of exactly 8 passing
        QuestionPart.objects.create(
            question=question,
            label="",
            order=1,
            prompt="""The probability of a person passing the driver test is 0.48. There are 13 people taking the driving test in a particular test centre today. Find the probability, to 5 decimal places, that exactly 8 of them pass their test.""",
            answer="0.10880",
            expected_format="Give your answer as a decimal rounded to 5 decimal places.",
            expected_type="numeric",
            max_marks=10,
            solution="""
**Step 1: Identify the distribution**

This is a **Binomial Distribution** problem with:
- $n = 13$ (number of people taking the test)
- $r = 8$ (number we want to pass)
- $p = 0.48$ (probability of passing)
- $q = 1 - p = 0.52$ (probability of failing)

**Step 2: Apply the Binomial Probability Formula**

$$P(X = r) = \\binom{n}{r} p^r (1-p)^{n-r}$$

$$P(X = 8) = \\binom{13}{8} (0.48)^8 (0.52)^{13-8}$$

$$P(X = 8) = \\binom{13}{8} (0.48)^8 (0.52)^5$$

**Step 3: Calculate the combination**

$$\\binom{13}{8} = \\frac{13!}{8!(13-8)!} = \\frac{13!}{8! \\cdot 5!}$$

$$\\binom{13}{8} = \\frac{13 \\times 12 \\times 11 \\times 10 \\times 9}{5 \\times 4 \\times 3 \\times 2 \\times 1} = \\frac{154440}{120} = 1287$$

**Step 4: Calculate the probability**

$$P(X = 8) = 1287 \\times (0.48)^8 \\times (0.52)^5$$

Calculate each part:
- $(0.48)^8 = 0.002814...$
- $(0.52)^5 = 0.038068...$
- $1287 \\times 0.002814... \\times 0.038068... = 0.10880...$

$$P(X = 8) = 0.10880$$

**Answer: 0.10880**

**Interpretation:** There is approximately a 10.88% chance that exactly 8 out of 13 people will pass the driving test.

**Calculator Note:** On a calculator with binomial distribution functions, you can use:
- binompdf(13, 0.48, 8) ≈ 0.10880
            """,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Created Question {question.id}: Probability - Binomial Distribution (Driver Test)\n"
                f"   Order: {question.order}\n"
                f"   Section: {question.section}\n"
                f"   Parts: {question.parts.count()}\n"
            )
        )
