"""
Management command to add Question 147: kth Success in nth Trial - Bowling Strikes
"""
from django.core.management.base import BaseCommand
from interactive_lessons.models import Topic, Question, QuestionPart


class Command(BaseCommand):
    help = "Add Question 147: kth Success in nth Trial - Bowling Strikes"

    def handle(self, *args, **options):
        # Get Probability topic
        topic = Topic.objects.get(name="Probability")

        # Create Question 147
        question = Question.objects.create(
            topic=topic,
            order=49,
            section="kth Success in nth Trial",
            hint="""This is a **kth Success in nth Trial** problem (Negative Binomial Distribution).

**Given:**
- We want the **8th success** (8th strike) to occur on the **13th trial** (13th roll)
- $p = 0.46$ (probability of getting a strike on each bowl)
- $k = 8$ (number of successes we want)
- $n = 13$ (trial on which we want the kth success)

**Formula:**
$$P(\\text{kth success on nth trial}) = \\binom{n-1}{k-1} p^k (1-p)^{n-k}$$

**Key Insight:**
- The **13th roll MUST be a strike** (the 8th strike)
- The first 12 rolls must contain exactly 7 strikes (and 5 non-strikes)
- This is why we use $\\binom{n-1}{k-1} = \\binom{12}{7}$""",
        )

        # Single part - Find probability of 8th strike on 13th roll
        QuestionPart.objects.create(
            question=question,
            label="",
            order=1,
            prompt="""A bowler gets a strike on 46% of their bowls. What is the probability, to four decimal places, that the bowler will get their eighth strike on their thirteenth roll?""",
            answer="0.1066",
            expected_format="Give your answer as a decimal rounded to 4 decimal places.",
            expected_type="numeric",
            max_marks=10,
            solution="""
**Step 1: Identify the problem type**

This is a **kth Success in nth Trial** problem (Negative Binomial Distribution).

We want to find the probability that the **8th success** (8th strike) occurs on the **13th roll**.

**Given:**
- $k = 8$ (number of successes/strikes we want)
- $n = 13$ (roll number where we want the kth success)
- $p = 0.46$ (probability of getting a strike)
- $q = 1 - p = 0.54$ (probability of not getting a strike)

**Step 2: Understand the constraint**

For the 8th strike to occur on the 13th roll:
- The **13th roll MUST be a strike** (the 8th strike)
- Among the **first 12 rolls**, exactly **7 must be strikes** (and 5 non-strikes)

**Step 3: Apply the formula**

$$P(\\text{8th strike on 13th roll}) = \\binom{n-1}{k-1} p^k (1-p)^{n-k}$$

$$P = \\binom{13-1}{8-1} (0.46)^8 (0.54)^{13-8}$$

$$P = \\binom{12}{7} (0.46)^8 (0.54)^5$$

**Step 4: Calculate the combination**

$$\\binom{12}{7} = \\frac{12!}{7!(12-7)!} = \\frac{12!}{7! \\cdot 5!}$$

$$\\binom{12}{7} = \\frac{12 \\times 11 \\times 10 \\times 9 \\times 8}{5 \\times 4 \\times 3 \\times 2 \\times 1}$$

$$\\binom{12}{7} = \\frac{95040}{120} = 792$$

**Step 5: Calculate the probability (use calculator for accuracy)**

$$P = 792 \\times (0.46)^8 \\times (0.54)^5$$

Using a calculator with full precision:
- $\\binom{12}{7} = 792$
- $(0.46)^8 = 0.00294499...$
- $(0.54)^5 = 0.04590...$
- $792 \\times 0.00294499... \\times 0.04590... = 0.1066...$

$$P = 0.1066$$

**Answer: 0.1066**

**Interpretation:** There is approximately a 10.66% chance that the bowler will get their 8th strike on their 13th roll.

**Why this formula works:**

Breaking it down:
1. The **13th roll must be a strike** (the 8th success): contributes $p = 0.46$
2. In the **first 12 rolls**, exactly **7 must be strikes**: contributes $\\binom{12}{7}(0.46)^7(0.54)^5$
3. Multiply together: $(0.46) \\times \\binom{12}{7}(0.46)^7(0.54)^5 = \\binom{12}{7}(0.46)^8(0.54)^5$

**General Formula:** For the **kth success** to occur on the **nth trial**:
$$P(X = n) = \\binom{n-1}{k-1} p^k (1-p)^{n-k}$$

where:
- The last trial (nth) must be a success
- The first $(n-1)$ trials must contain exactly $(k-1)$ successes

**Remember:**
- **"k successes IN n trials"** → Regular Binomial: $\\binom{n}{k}p^k(1-p)^{n-k}$
- **"kth success ON the nth trial"** → Negative Binomial: $\\binom{n-1}{k-1}p^k(1-p)^{n-k}$
            """,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Created Question {question.id}: Probability - kth Success in nth Trial (Bowling Strikes)\n"
                f"   Order: {question.order}\n"
                f"   Section: {question.section}\n"
                f"   Parts: {question.parts.count()}\n"
            )
        )
