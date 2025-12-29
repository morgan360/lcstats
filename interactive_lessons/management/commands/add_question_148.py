"""
Management command to add Question 148: Probability of Events Occurring At Least Once
"""
from django.core.management.base import BaseCommand
from interactive_lessons.models import Topic, Question, QuestionPart


class Command(BaseCommand):
    help = "Add Question 148: Probability of Events Occurring At Least Once"

    def handle(self, *args, **options):
        # Get Probability topic
        topic = Topic.objects.get(name="Probability")

        # Create Question 148
        question = Question.objects.create(
            topic=topic,
            order=50,
            section="Probability of Events Occurring At Least Once",
            hint="""This is an **"At Least One"** probability problem with **independent events**.

**Given:**
- Student 1: $P(\\text{pass}) = \\frac{3}{5}$
- Student 2: $P(\\text{pass}) = \\frac{1}{2}$
- Student 3: $P(\\text{pass}) = \\frac{5}{6}$

**Key Strategy:** Use the **complement rule**.

"At least one passes" is easier to calculate using:
$$P(\\text{at least one passes}) = 1 - P(\\text{none pass})$$

**Steps:**
1. Find $P(\\text{each student fails})$
2. Calculate $P(\\text{all three fail})$ using independence
3. Use complement: $P(\\text{at least one passes}) = 1 - P(\\text{all fail})$""",
        )

        # Single part - Find probability at least one passes
        QuestionPart.objects.create(
            question=question,
            label="",
            order=1,
            prompt="""Three students are taking an English exam. The probability that they each pass is $\\frac{3}{5}$, $\\frac{1}{2}$, and $\\frac{5}{6}$ respectively. What is the probability that at least one of the students passes the exam?""",
            answer="29/30",
            expected_format="Give your answer as a fraction in simplest form.",
            expected_type="exact",
            max_marks=10,
            solution="""
**Step 1: Identify the approach**

"At least one passes" means **one OR two OR all three** pass.

Instead of calculating all these cases separately, use the **complement rule**:
$$P(\\text{at least one passes}) = 1 - P(\\text{none pass})$$

**Step 2: Find probability each student fails**

Since the students are **independent**:
- Student 1: $P(\\text{fail}) = 1 - \\frac{3}{5} = \\frac{2}{5}$
- Student 2: $P(\\text{fail}) = 1 - \\frac{1}{2} = \\frac{1}{2}$
- Student 3: $P(\\text{fail}) = 1 - \\frac{5}{6} = \\frac{1}{6}$

**Step 3: Calculate probability all three fail**

Since the students are independent, multiply:
$$P(\\text{all fail}) = P(\\text{S1 fails}) \\times P(\\text{S2 fails}) \\times P(\\text{S3 fails})$$

$$P(\\text{all fail}) = \\frac{2}{5} \\times \\frac{1}{2} \\times \\frac{1}{6}$$

$$P(\\text{all fail}) = \\frac{2 \\times 1 \\times 1}{5 \\times 2 \\times 6} = \\frac{2}{60} = \\frac{1}{30}$$

**Step 4: Apply the complement rule**

$$P(\\text{at least one passes}) = 1 - P(\\text{all fail})$$

$$P(\\text{at least one passes}) = 1 - \\frac{1}{30}$$

$$P(\\text{at least one passes}) = \\frac{30}{30} - \\frac{1}{30} = \\frac{29}{30}$$

**Answer: $\\frac{29}{30}$**

**Interpretation:** There is a $\\frac{29}{30}$ chance (approximately 96.67%) that at least one of the three students passes the English exam.

**Key Concept - The Complement Rule for "At Least One":**

When dealing with "at least one" problems:
$$P(\\text{at least one success}) = 1 - P(\\text{no successes})$$

This is **much easier** than calculating $P(\\text{exactly 1}) + P(\\text{exactly 2}) + P(\\text{exactly 3})$.

**Why use the complement?**

If we tried to calculate directly:
- $P(\\text{exactly 1 passes})$ requires considering which one passes (3 cases)
- $P(\\text{exactly 2 pass})$ requires considering which two pass (3 cases)
- $P(\\text{all 3 pass})$ is just 1 case

That's 7 different calculations! Using the complement (none pass) is just 1 simple calculation.
            """,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Created Question {question.id}: Probability - At Least One Event Occurs\n"
                f"   Order: {question.order}\n"
                f"   Section: {question.section}\n"
                f"   Parts: {question.parts.count()}\n"
            )
        )
