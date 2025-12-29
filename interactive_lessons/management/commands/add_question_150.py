"""
Management command to add Question 150: At Least One - Darts Bullseye
"""
from django.core.management.base import BaseCommand
from interactive_lessons.models import Topic, Question, QuestionPart


class Command(BaseCommand):
    help = "Add Question 150: At Least One - Darts Bullseye"

    def handle(self, *args, **options):
        # Get Probability topic
        topic = Topic.objects.get(name="Probability")

        # Create Question 150
        question = Question.objects.create(
            topic=topic,
            order=52,
            section="Probability of Events Occurring At Least Once",
            hint="""This is an **"At Least One"** probability problem with **independent events**.

**Given:**
- Player 1: $P(\\text{hits bullseye}) = \\frac{3}{4}$
- Player 2: $P(\\text{hits bullseye}) = \\frac{1}{5}$
- Player 3: $P(\\text{hits bullseye}) = \\frac{2}{9}$
- Player 4: $P(\\text{hits bullseye}) = \\frac{7}{10}$

**Key Strategy:** Use the **complement rule**.

"At least one hits" is easier to calculate using:
$$P(\\text{at least one hits}) = 1 - P(\\text{none hit})$$

**Steps:**
1. Find $P(\\text{each player misses})$
2. Calculate $P(\\text{all four miss})$ by multiplying (independence)
3. Use complement: $P(\\text{at least one hits}) = 1 - P(\\text{all miss})$""",
        )

        # Single part - Find probability at least one hits
        QuestionPart.objects.create(
            question=question,
            label="",
            order=1,
            prompt="""The probability that 4 darts players hit the bullseye is $\\frac{3}{4}$, $\\frac{1}{5}$, $\\frac{2}{9}$, and $\\frac{7}{10}$ respectively. Work out the probability that at least one of the players hits the bullseye.""",
            answer="143/150",
            expected_format="Give your answer as a fraction in simplest form.",
            expected_type="exact",
            max_marks=10,
            solution="""
**Step 1: Identify the approach**

"At least one hits the bullseye" means **one OR two OR three OR all four** hit.

Instead of calculating all these cases separately, use the **complement rule**:
$$P(\\text{at least one hits}) = 1 - P(\\text{none hit})$$

**Step 2: Find probability each player misses**

Since the players are **independent**:
- Player 1: $P(\\text{miss}) = 1 - \\frac{3}{4} = \\frac{1}{4}$
- Player 2: $P(\\text{miss}) = 1 - \\frac{1}{5} = \\frac{4}{5}$
- Player 3: $P(\\text{miss}) = 1 - \\frac{2}{9} = \\frac{7}{9}$
- Player 4: $P(\\text{miss}) = 1 - \\frac{7}{10} = \\frac{3}{10}$

**Step 3: Calculate probability all four miss**

Since the players are independent, multiply:
$$P(\\text{all miss}) = P(\\text{P1 misses}) \\times P(\\text{P2 misses}) \\times P(\\text{P3 misses}) \\times P(\\text{P4 misses})$$

$$P(\\text{all miss}) = \\frac{1}{4} \\times \\frac{4}{5} \\times \\frac{7}{9} \\times \\frac{3}{10}$$

Multiply numerators: $1 \\times 4 \\times 7 \\times 3 = 84$

Multiply denominators: $4 \\times 5 \\times 9 \\times 10 = 1800$

$$P(\\text{all miss}) = \\frac{84}{1800}$$

Simplify by finding $\\gcd(84, 1800) = 12$:
$$P(\\text{all miss}) = \\frac{84 \\div 12}{1800 \\div 12} = \\frac{7}{150}$$

**Step 4: Apply the complement rule**

$$P(\\text{at least one hits}) = 1 - P(\\text{all miss})$$

$$P(\\text{at least one hits}) = 1 - \\frac{7}{150}$$

$$P(\\text{at least one hits}) = \\frac{150 - 7}{150} = \\frac{143}{150}$$

Since $\\gcd(143, 150) = 1$, this fraction is already in simplest form.

**Answer: $\\frac{143}{150}$**

**Interpretation:** There is a $\\frac{143}{150}$ chance (approximately 95.33%) that at least one of the four darts players hits the bullseye.

**Key Concept - The Complement Rule:**

For "at least one" problems:
$$P(\\text{at least one success}) = 1 - P(\\text{all fail})$$

This avoids calculating 15 different combinations (which specific players hit)!
            """,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Created Question {question.id}: Probability - At Least One (Darts Bullseye)\n"
                f"   Order: {question.order}\n"
                f"   Section: {question.section}\n"
                f"   Parts: {question.parts.count()}\n"
            )
        )
