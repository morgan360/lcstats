"""
Management command to add Question 146: kth Success in nth Trial - Driving Theory Test
"""
from django.core.management.base import BaseCommand
from interactive_lessons.models import Topic, Question, QuestionPart


class Command(BaseCommand):
    help = "Add Question 146: kth Success in nth Trial - Driving Theory Test"

    def handle(self, *args, **options):
        # Get Probability topic
        topic = Topic.objects.get(name="Probability")

        # Create Question 146
        question = Question.objects.create(
            topic=topic,
            order=48,
            section="kth Success in nth Trial",
            hint="""This is a **kth Success in nth Trial** problem (Negative Binomial Distribution).

**Given:**
- We want the **6th success** (6th person to pass) to be the **10th trial** (10th person to take the test)
- $p = 0.67$ (probability of passing)
- $k = 6$ (number of successes we want)
- $n = 10$ (trial on which we want the kth success)

**Formula:**
$$P(\\text{kth success on nth trial}) = \\binom{n-1}{k-1} p^k (1-p)^{n-k}$$

**Key Insight:**
- The **10th person MUST pass** (the 6th success)
- The first 9 people must contain exactly 5 passes (and 4 failures)
- This is why we use $\\binom{n-1}{k-1} = \\binom{9}{5}$""",
        )

        # Single part - Find probability of 6th pass on 10th person
        QuestionPart.objects.create(
            question=question,
            label="",
            order=1,
            prompt="""The probability that a randomly selected person passes their driving theory test is 0.67. What is the probability, to six decimal places, that on a random day the sixth person to pass the test will be the tenth person to take the test that day?""",
            answer="0.177688",
            expected_format="Give your answer as a decimal rounded to 6 decimal places.",
            expected_type="numeric",
            max_marks=10,
            solution="""
**Step 1: Identify the problem type**

This is a **kth Success in nth Trial** problem (Negative Binomial Distribution).

We want to find the probability that the **6th success** (6th person to pass) is the **10th person** to take the test.

**Given:**
- $k = 6$ (number of successes/passes we want)
- $n = 10$ (person number where we want the kth success)
- $p = 0.67$ (probability of passing)
- $q = 1 - p = 0.33$ (probability of failing)

**Step 2: Understand the constraint**

For the 6th person to pass on the 10th person tested:
- The **10th person MUST pass** (the 6th success)
- Among the **first 9 people**, exactly **5 must pass** (and 4 must fail)

**Step 3: Apply the formula**

$$P(\\text{6th pass on 10th person}) = \\binom{n-1}{k-1} p^k (1-p)^{n-k}$$

$$P = \\binom{10-1}{6-1} (0.67)^6 (0.33)^{10-6}$$

$$P = \\binom{9}{5} (0.67)^6 (0.33)^4$$

**Step 4: Calculate the combination**

$$\\binom{9}{5} = \\frac{9!}{5!(9-5)!} = \\frac{9!}{5! \\cdot 4!}$$

$$\\binom{9}{5} = \\frac{9 \\times 8 \\times 7 \\times 6}{4 \\times 3 \\times 2 \\times 1} = \\frac{3024}{24} = 126$$

**Step 5: Calculate the probability (use calculator for accuracy)**

$$P = 126 \\times (0.67)^6 \\times (0.33)^4$$

Using a calculator with full precision:
- $\\binom{9}{5} = 126$
- $(0.67)^6 = 0.0905493...$
- $(0.33)^4 = 0.0118587...$
- $126 \\times 0.0905493... \\times 0.0118587... = 0.177688...$

$$P = 0.177688$$

**Answer: 0.177688**

**Interpretation:** There is approximately a 17.77% chance that the 6th person to pass the driving theory test will be the 10th person to take it on a random day.

**Why this formula works:**

Breaking it down:
1. The **10th person must pass** (the 6th success): contributes $p = 0.67$
2. In the **first 9 people**, exactly **5 must pass**: contributes $\\binom{9}{5}(0.67)^5(0.33)^4$
3. Multiply together: $(0.67) \\times \\binom{9}{5}(0.67)^5(0.33)^4 = \\binom{9}{5}(0.67)^6(0.33)^4$

**General Formula:** For the **kth success** to occur on the **nth trial**:
$$P(X = n) = \\binom{n-1}{k-1} p^k (1-p)^{n-k}$$

**Key difference from regular Binomial:**
- **Regular Binomial:** "Exactly k successes **in** n trials" → $\\binom{n}{k}p^k(1-p)^{n-k}$
- **kth Success in nth Trial:** "kth success occurs **on** the nth trial" → $\\binom{n-1}{k-1}p^k(1-p)^{n-k}$
            """,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Created Question {question.id}: Probability - kth Success in nth Trial (Driving Theory Test)\n"
                f"   Order: {question.order}\n"
                f"   Section: {question.section}\n"
                f"   Parts: {question.parts.count()}\n"
            )
        )
