"""
Management command to add Question 133: Independent Events - Venn Diagram (find x)
"""
from django.core.management.base import BaseCommand
from interactive_lessons.models import Topic, Question, QuestionPart


class Command(BaseCommand):
    help = "Add Question 133: Independent Events - Venn Diagram (find x)"

    def handle(self, *args, **options):
        # Get Probability topic
        topic = Topic.objects.get(name="Probability")

        # Create Question 133
        question = Question.objects.create(
            topic=topic,
            order=37,
            section="Independent Events",
            hint="For events to be independent, $P(C \\cap D) = P(C) \\times P(D)$. Use the Venn diagram to find these probabilities in terms of $x$, then solve for $x$.",
        )

        # Single part - find value of x
        QuestionPart.objects.create(
            question=question,
            label="",
            order=1,
            prompt="Find the value of $x$ for which the events C and D below are independent.",
            answer="0.15",
            expected_format="Give your answer as a decimal.",
            expected_type="numeric",
            max_marks=10,
            solution="""
**Independence Test:** For events C and D to be independent:
$$P(C \\cap D) = P(C) \\times P(D)$$

**Step 1: Read probabilities from the Venn diagram**

From the diagram:
- $P(C \\cap D) = 0.1$ (the intersection region)
- $P(C) = x + 0.1$ (all of circle C: the $x$ region plus the intersection)
- $P(D) = 0.1 + 0.3 = 0.4$ (all of circle D: the intersection plus the 0.3 region)

**Step 2: Apply the independence condition**

$$P(C \\cap D) = P(C) \\times P(D)$$
$$0.1 = (x + 0.1) \\times 0.4$$

**Step 3: Solve for x**

$$0.1 = 0.4x + 0.04$$
$$0.1 - 0.04 = 0.4x$$
$$0.06 = 0.4x$$
$$x = \\frac{0.06}{0.4} = \\frac{6}{40} = \\frac{3}{20} = 0.15$$

**Step 4: Verify the answer**

Check: If $x = 0.15$, then:
- $P(C) = 0.15 + 0.1 = 0.25$
- $P(D) = 0.4$
- $P(C) \\times P(D) = 0.25 \\times 0.4 = 0.1$ ✓

This equals $P(C \\cap D) = 0.1$, confirming independence.

**Answer: $x = 0.15$**
            """,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Created Question {question.id}: Probability - Independent Events (Find x from Venn Diagram)\n"
                f"   Order: {question.order}\n"
                f"   Section: {question.section}\n"
                f"   Parts: {question.parts.count()}\n"
            )
        )
        self.stdout.write(
            self.style.WARNING(
                "⚠️  REMINDER: Upload the Venn diagram image through admin:\n"
                "   - Go to Question 133 in admin\n"
                "   - Upload the Venn diagram to the 'image' field\n"
            )
        )