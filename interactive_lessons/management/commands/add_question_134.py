"""
Management command to add Question 134: Independent Events - Find P(B)
"""
from django.core.management.base import BaseCommand
from interactive_lessons.models import Topic, Question, QuestionPart


class Command(BaseCommand):
    help = "Add Question 134: Independent Events - Find P(B)"

    def handle(self, *args, **options):
        # Get Probability topic
        topic = Topic.objects.get(name="Probability")

        # Create Question 134
        question = Question.objects.create(
            topic=topic,
            order=38,
            section="Independent Events",
            hint="Use the formula $P(A \\cup B) = P(A) + P(B) - P(A \\cap B)$. For independent events, $P(A \\cap B) = P(A) \\times P(B)$.",
        )

        # Single part - find P(B)
        QuestionPart.objects.create(
            question=question,
            label="",
            order=1,
            prompt="$A$ and $B$ are independent events such that $P(A \\cup B) = 0.8$ and $P(A) = 0.3$. Find $P(B)$.",
            answer="0.714",
            expected_format="Give your answer as a decimal rounded to 3 decimal places.",
            expected_type="numeric",
            max_marks=10,
            solution="""
**Given:**
- $A$ and $B$ are independent events
- $P(A \\cup B) = 0.8$
- $P(A) = 0.3$
- Find: $P(B)$

**Step 1: Use the Addition Rule for Probability**

$$P(A \\cup B) = P(A) + P(B) - P(A \\cap B)$$

**Step 2: Apply Independence**

Since $A$ and $B$ are independent:
$$P(A \\cap B) = P(A) \\times P(B)$$

**Step 3: Substitute into the Addition Rule**

$$P(A \\cup B) = P(A) + P(B) - P(A) \\times P(B)$$

Substitute the known values:
$$0.8 = 0.3 + P(B) - 0.3 \\times P(B)$$

**Step 4: Solve for P(B)**

$$0.8 = 0.3 + P(B) - 0.3P(B)$$
$$0.8 = 0.3 + P(B)(1 - 0.3)$$
$$0.8 = 0.3 + 0.7P(B)$$
$$0.8 - 0.3 = 0.7P(B)$$
$$0.5 = 0.7P(B)$$
$$P(B) = \\frac{0.5}{0.7}$$
$$P(B) = \\frac{5}{7}$$
$$P(B) \\approx 0.714$$

**Step 5: Verify the answer**

Check: If $P(B) = 5/7$, then:
- $P(A \\cap B) = 0.3 \\times \\frac{5}{7} = \\frac{1.5}{7} = \\frac{3}{14}$
- $P(A \\cup B) = 0.3 + \\frac{5}{7} - \\frac{3}{14}$
- $P(A \\cup B) = \\frac{3}{10} + \\frac{5}{7} - \\frac{3}{14}$

Converting to common denominator 70:
- $P(A \\cup B) = \\frac{21}{70} + \\frac{50}{70} - \\frac{15}{70} = \\frac{56}{70} = \\frac{4}{5} = 0.8$ ✓

**Answer: $P(B) = \\frac{5}{7} \\approx 0.714$**
            """,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Created Question {question.id}: Probability - Independent Events (Find P(B))\n"
                f"   Order: {question.order}\n"
                f"   Section: {question.section}\n"
                f"   Parts: {question.parts.count()}\n"
            )
        )
