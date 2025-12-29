"""
Management command to add Question 145: kth Success in nth Trial - Mbappe Goals
"""
from django.core.management.base import BaseCommand
from interactive_lessons.models import Topic, Question, QuestionPart


class Command(BaseCommand):
    help = "Add Question 145: kth Success in nth Trial - Mbappe Goals"

    def handle(self, *args, **options):
        # Get Probability topic
        topic = Topic.objects.get(name="Probability")

        # Create Question 145
        question = Question.objects.create(
            topic=topic,
            order=47,
            section="kth Success in nth Trial",
            hint="""This is a **kth Success in nth Trial** problem (also called Negative Binomial).

**Given:**
- We want the **9th success** (9th goal) to occur on the **12th trial** (12th shot)
- $p = 0.71$ (probability of scoring on each shot)
- $k = 9$ (number of successes we want)
- $n = 12$ (trial on which we want the kth success)

**Formula:**
$$P(\\text{kth success on nth trial}) = \\binom{n-1}{k-1} p^k (1-p)^{n-k}$$

**Key Insight:**
- The **last trial (12th shot) MUST be a success** (the 9th goal)
- The first 11 shots must contain exactly 8 successes (goals)
- This is why we use $\\binom{n-1}{k-1}$ instead of $\\binom{n}{k}$""",
        )

        # Single part - Find probability of 9th goal on 12th shot
        QuestionPart.objects.create(
            question=question,
            label="",
            order=1,
            prompt="""Kylian Mbappe scores 71% of his shots on goal. What is the probability, correct to four decimal places, that he scores his ninth goal on his twelfth shot?""",
            answer="0.1348",
            expected_format="Give your answer as a decimal rounded to 4 decimal places.",
            expected_type="numeric",
            max_marks=10,
            solution="""
**Step 1: Identify the problem type**

This is a **kth Success in nth Trial** problem (Negative Binomial Distribution).

We want to find the probability that the **9th success** (9th goal) occurs on the **12th trial** (12th shot).

**Given:**
- $k = 9$ (number of successes/goals we want)
- $n = 12$ (trial number where we want the kth success)
- $p = 0.71$ (probability of scoring on each shot)
- $q = 1 - p = 0.29$ (probability of missing)

**Step 2: Understand the constraint**

For the 9th goal to occur on the 12th shot:
- The **12th shot MUST be a goal** (the 9th success)
- In the **first 11 shots**, there must be **exactly 8 goals** (and 3 misses)

**Step 3: Apply the formula**

$$P(\\text{9th goal on 12th shot}) = \\binom{n-1}{k-1} p^k (1-p)^{n-k}$$

$$P = \\binom{12-1}{9-1} (0.71)^9 (0.29)^{12-9}$$

$$P = \\binom{11}{8} (0.71)^9 (0.29)^3$$

**Step 4: Calculate the combination**

$$\\binom{11}{8} = \\frac{11!}{8!(11-8)!} = \\frac{11!}{8! \\cdot 3!}$$

$$\\binom{11}{8} = \\frac{11 \\times 10 \\times 9}{3 \\times 2 \\times 1} = \\frac{990}{6} = 165$$

**Step 5: Calculate the probability (use calculator for accuracy)**

$$P = 165 \\times (0.71)^9 \\times (0.29)^3$$

Using a calculator with full precision:
- $\\binom{11}{8} = 165$
- $(0.71)^9 = 0.0244898...$
- $(0.29)^3 = 0.024389$
- $165 \\times 0.0244898... \\times 0.024389 = 0.1348...$

$$P = 0.1348$$

**Answer: 0.1348**

**Interpretation:** There is approximately a 13.48% chance that Kylian Mbappe scores his 9th goal on his 12th shot.

**Why this formula?**

Think of it this way:
1. The 12th shot **must** be a goal (the 9th one): probability = $p = 0.71$
2. In the first 11 shots, we need exactly 8 goals: probability = $\\binom{11}{8}(0.71)^8(0.29)^3$
3. Multiply these together: $p \\times \\binom{11}{8}(0.71)^8(0.29)^3 = \\binom{11}{8}(0.71)^9(0.29)^3$

**General Formula:** For the **kth success** to occur on the **nth trial**:
$$P(X = n) = \\binom{n-1}{k-1} p^k (1-p)^{n-k}$$

where:
- The last trial must be a success
- The first $(n-1)$ trials must contain exactly $(k-1)$ successes
            """,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Created Question {question.id}: Probability - kth Success in nth Trial (Mbappe Goals)\n"
                f"   Order: {question.order}\n"
                f"   Section: {question.section}\n"
                f"   Parts: {question.parts.count()}\n"
            )
        )
