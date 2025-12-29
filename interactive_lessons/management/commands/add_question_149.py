"""
Management command to add Question 149: At Least One - Penalty Shootout
"""
from django.core.management.base import BaseCommand
from interactive_lessons.models import Topic, Question, QuestionPart


class Command(BaseCommand):
    help = "Add Question 149: At Least One - Penalty Shootout"

    def handle(self, *args, **options):
        # Get Probability topic
        topic = Topic.objects.get(name="Probability")

        # Create Question 149
        question = Question.objects.create(
            topic=topic,
            order=51,
            section="Probability of Events Occurring At Least Once",
            hint="""This is an **"At Least One"** probability problem with **independent events**.

**Given:**
- Taker 1: $P(\\text{scores}) = \\frac{4}{5}$
- Taker 2: $P(\\text{scores}) = \\frac{5}{8}$
- Taker 3: $P(\\text{scores}) = \\frac{2}{3}$
- Taker 4: $P(\\text{scores}) = \\frac{4}{7}$
- Taker 5: $P(\\text{scores}) = \\frac{9}{10}$

**Key Strategy:** Use the **complement rule**.

"At least one scores" is easier to calculate using:
$$P(\\text{at least one scores}) = 1 - P(\\text{none score})$$

**Steps:**
1. Find $P(\\text{each taker misses})$
2. Calculate $P(\\text{all five miss})$ by multiplying (independence)
3. Use complement: $P(\\text{at least one scores}) = 1 - P(\\text{all miss})$""",
        )

        # Single part - Find probability at least one scores
        QuestionPart.objects.create(
            question=question,
            label="",
            order=1,
            prompt="""Manchester United are in a penalty shoot-out to win the Champions League. The probability that each of the takers scores their penalty is $\\frac{4}{5}$, $\\frac{5}{8}$, $\\frac{2}{3}$, $\\frac{4}{7}$, and $\\frac{9}{10}$ respectively. Work out the probability that at least one of the penalty takers score a penalty.""",
            answer="2797/2800",
            expected_format="Give your answer as a fraction in simplest form.",
            expected_type="exact",
            max_marks=10,
            solution="""
**Step 1: Identify the approach**

"At least one scores" means **one OR two OR three OR four OR all five** score.

Instead of calculating all these cases separately, use the **complement rule**:
$$P(\\text{at least one scores}) = 1 - P(\\text{none score})$$

**Step 2: Find probability each taker misses**

Since the penalty takers are **independent**:
- Taker 1: $P(\\text{miss}) = 1 - \\frac{4}{5} = \\frac{1}{5}$
- Taker 2: $P(\\text{miss}) = 1 - \\frac{5}{8} = \\frac{3}{8}$
- Taker 3: $P(\\text{miss}) = 1 - \\frac{2}{3} = \\frac{1}{3}$
- Taker 4: $P(\\text{miss}) = 1 - \\frac{4}{7} = \\frac{3}{7}$
- Taker 5: $P(\\text{miss}) = 1 - \\frac{9}{10} = \\frac{1}{10}$

**Step 3: Calculate probability all five miss**

Since the takers are independent, multiply:
$$P(\\text{all miss}) = P(\\text{T1 misses}) \\times P(\\text{T2 misses}) \\times P(\\text{T3 misses}) \\times P(\\text{T4 misses}) \\times P(\\text{T5 misses})$$

$$P(\\text{all miss}) = \\frac{1}{5} \\times \\frac{3}{8} \\times \\frac{1}{3} \\times \\frac{3}{7} \\times \\frac{1}{10}$$

Multiply numerators: $1 \\times 3 \\times 1 \\times 3 \\times 1 = 9$

Multiply denominators: $5 \\times 8 \\times 3 \\times 7 \\times 10 = 8400$

$$P(\\text{all miss}) = \\frac{9}{8400}$$

Simplify by finding $\\gcd(9, 8400) = 3$:
$$P(\\text{all miss}) = \\frac{9 \\div 3}{8400 \\div 3} = \\frac{3}{2800}$$

**Step 4: Apply the complement rule**

$$P(\\text{at least one scores}) = 1 - P(\\text{all miss})$$

$$P(\\text{at least one scores}) = 1 - \\frac{3}{2800}$$

$$P(\\text{at least one scores}) = \\frac{2800 - 3}{2800} = \\frac{2797}{2800}$$

Since $\\gcd(2797, 2800) = 1$, this fraction is already in simplest form.

**Answer: $\\frac{2797}{2800}$**

**Interpretation:** There is a $\\frac{2797}{2800}$ chance (approximately 99.89%) that at least one Manchester United penalty taker scores in the shootout.

**Key Concept - The Complement Rule:**

For "at least one" problems:
$$P(\\text{at least one success}) = 1 - P(\\text{all fail})$$

This avoids calculating 31 different combinations (1 scores, 2 score, 3 score, 4 score, or all 5 score)!
            """,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Created Question {question.id}: Probability - At Least One (Penalty Shootout)\n"
                f"   Order: {question.order}\n"
                f"   Section: {question.section}\n"
                f"   Parts: {question.parts.count()}\n"
            )
        )
