"""
Management command to add Question 139: Bernoulli Trials - Missing Condition
"""
from django.core.management.base import BaseCommand
from interactive_lessons.models import Topic, Question, QuestionPart


class Command(BaseCommand):
    help = "Add Question 139: Bernoulli Trials - Missing Condition"

    def handle(self, *args, **options):
        # Get Probability topic
        topic = Topic.objects.get(name="Probability")

        # Create Question 139
        question = Question.objects.create(
            topic=topic,
            order=41,
            section="Bernoulli Trials",
            hint="""**What are Bernoulli Trials?**

A **Bernoulli Trial** is a random experiment where there are only two possible outcomes: success or failure. A sequence of Bernoulli trials must satisfy **four conditions**:

**1. Fixed Number of Trials**
   - The number of trials, $n$, is determined in advance and remains constant.
   - Example: Flipping a coin 10 times (not "flip until you get heads").

**2. Only Two Outcomes**
   - Each trial has exactly two possible outcomes: success (S) or failure (F).
   - Example: Pass/Fail, Heads/Tails, Win/Lose, Yes/No.

**3. Independent Trials**
   - The outcome of one trial does not affect the outcome of any other trial.
   - Example: Drawing cards **with replacement** (not without replacement).

**4. Constant Probability**
   - The probability of success, $p$, remains the same for every trial.
   - The probability of failure is $q = 1 - p$.
   - Example: A fair coin always has $P(\\text{Heads}) = 0.5$ on every flip.

**Common Applications:**
- Coin flips (Heads/Tails)
- Free throw shooting (Make/Miss)
- Quality control (Defective/Non-defective)
- Medical trials (Cure/No cure)

**The Binomial Distribution**

When we conduct $n$ Bernoulli trials with success probability $p$, the number of successes follows a **Binomial Distribution** with probability:

$$P(X = r) = \\binom{n}{r} p^r (1-p)^{n-r}$$

where $r$ is the number of successes.

**Example:** Rolling a die 5 times and counting how many 6's appear satisfies all four conditions:
1. ✓ Fixed number: 5 rolls
2. ✓ Two outcomes: Six (success) or Not-Six (failure)
3. ✓ Independent: Each roll doesn't affect the next
4. ✓ Constant probability: $P(6) = \\frac{1}{6}$ on every roll""",
        )

        # Multiple choice question
        QuestionPart.objects.create(
            question=question,
            label="",
            order=1,
            prompt="""Three of the four conditions for a Bernoulli Trial are listed below. Which one is missing?

1. A fixed number of trials
2. Only two outcomes in the trial - success or failure
3. The trials are independent

**Choose the missing condition:**

(a) The probability of success must be greater than 0.5

(b) The probability of success remains constant for each trial

(c) Each trial must take the same amount of time

(d) The trials must be performed in sequence""",
            answer="b",
            expected_format="Enter the letter of your answer (a, b, c, or d).",
            expected_type="exact",
            max_marks=5,
            solution="""
The **four conditions** for Bernoulli Trials are:

1. ✓ **Fixed number of trials** (given in the question)
2. ✓ **Only two outcomes** - success or failure (given in the question)
3. ✓ **Independent trials** (given in the question)
4. ⭐ **Constant probability of success** - the probability $p$ must remain the same for every trial

**Analysis of options:**

**(a) The probability of success must be greater than 0.5**
- ✗ INCORRECT: The probability of success can be any value between 0 and 1. It does not need to be greater than 0.5.
- Example: Rolling a 6 on a fair die has $p = \\frac{1}{6} < 0.5$ but is still a valid Bernoulli trial.

**(b) The probability of success remains constant for each trial**
- ✓ **CORRECT**: This is the fourth condition. The probability $p$ must stay the same throughout all trials.
- This is what distinguishes Bernoulli trials from other random experiments.

**(c) Each trial must take the same amount of time**
- ✗ INCORRECT: Time is not a factor in Bernoulli trials. The trials could take different amounts of time.

**(d) The trials must be performed in sequence**
- ✗ INCORRECT: The order doesn't matter. Bernoulli trials could theoretically be performed simultaneously, as long as they're independent.

**Answer: (b) The probability of success remains constant for each trial**

**Example of violating constant probability:**
Drawing cards from a deck **without replacement** violates this condition because:
- First draw: $P(\\text{Ace}) = \\frac{4}{52}$
- Second draw: $P(\\text{Ace}) = \\frac{3}{51}$ or $\\frac{4}{51}$ (depends on first card)

The probability changes, so this is NOT a Bernoulli trial.

**Example satisfying all conditions:**
Drawing cards **with replacement**:
- Fixed number (say, 10 draws)
- Two outcomes (Ace or Not-Ace)
- Independent (each card is replaced)
- Constant probability ($P(\\text{Ace}) = \\frac{4}{52} = \\frac{1}{13}$ every time)
            """,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Created Question {question.id}: Probability - Bernoulli Trials (Missing Condition)\n"
                f"   Order: {question.order}\n"
                f"   Section: {question.section}\n"
                f"   Parts: {question.parts.count()}\n"
            )
        )