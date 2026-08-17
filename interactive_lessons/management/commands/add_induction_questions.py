"""Add the Proof by Induction practice questions.

Content authored on local and replayed here so production gets exactly what was
tested. Idempotent: keyed on topic slug, section name and question order rather
than primary key, because ids differ between local and production. Re-running
updates in place and never duplicates.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Subject
from interactive_lessons.models import Topic, Question, QuestionPart, Section

TOPIC_SLUG = "proof-by-induction"
TOPIC_NAME = "Proof by Induction"
SUBJECT_NAME = "Maths"
PAPER = "p1"

# (section name, section order, [questions])
QUESTIONS = [
    ("""Divisibility""", 1, [
        {
            "order": 1,
            "hint": """**The three steps:** (1) *Base case* — prove $P(n)$ for the smallest $n$. (2) *Hypothesis* — assume $P(k)$ is true. (3) *Inductive step* — use that assumption to prove $P(k+1)$. For divisibility by $d$, rewrite $P(k+1)$ so that $P(k)$ appears as a factor and every remaining term contains $d$. Splitting the larger base (e.g., $7 = 4 + 3$) is the usual trick.""",
            "solution": None,
            "is_copyrighted": True,
            "is_exam_question": False,
            "is_quickkick_suitable": False,
            "parts": [
                {
                    "label": """(a)""",
                    "order": 0,
                    "prompt": r"""Let $P(n) = 7^n - 3^n$, where $n \in \mathbb{N}$.

Verify the **base case** by evaluating $P(1)$.""",
                    "answer": """4""",
                    "expected_format": """Single whole number (e.g., 6 or 12)""",
                    "expected_type": """numeric""",
                    "max_marks": 5,
                    "unlock": 2,
                    "scale": None,
                    "solution": r"""**Step 1:** Substitute $n = 1$ into $P(n) = 7^n - 3^n$.

$$P(1) = 7^1 - 3^1 = 7 - 3 = 4$$

**Step 2:** Check the divisor. Since $4 = 4 \times 1$, $P(1)$ is divisible by $4$.

So the base case holds.

**Answer:** $4$""",
                    "qk": False,
                },
                {
                    "label": """(b)""",
                    "order": 1,
                    "prompt": r"""In the inductive step you must show that $P(k+1) = 7^{k+1} - 3^{k+1}$ is divisible by **4**, given that $7^k - 3^k$ is divisible by **4**.

Starting from $7^{k+1} - 3^{k+1} = 7^k(7) - 3^k(3)$, which manipulation makes $P(k)$ appear as a factor?

**(A)** Split $7 = 8 - 1$, giving $8(7^k) - 7^k - 3^{k+1}$

**(B)** Split $7 = 5 + 2$, giving $5(7^k) + 2(7^k) - 3^{k+1}$

**(C)** Split $7 = 4 + 3$, giving $4(7^k) + 3\bigl(7^k - 3^k\bigr)$

**(D)** Split $3 = 7 - 4$, giving $7^{k+1} - 7^k(7) + 7^k(4)$

**Format your answer as:** Answer: [A/B/C/D]""",
                    "answer": """C""",
                    "expected_format": """Single letter (e.g., B or D)""",
                    "expected_type": """multi""",
                    "max_marks": 10,
                    "unlock": 2,
                    "scale": None,
                    "solution": r"""**Step 1:** The aim is to make the bracket $\bigl(7^k - 3^k\bigr)$ appear, because that is $P(k)$, which we have assumed is divisible by $4$.

**Step 2:** The term $-3^k(3)$ already carries a factor of $3$, so we need a matching $3(7^k)$. Splitting $7 = 4 + 3$ produces exactly that:

$$7^k(4 + 3) - 3^k(3) = 4(7^k) + 3(7^k) - 3(3^k)$$

**Step 3:** Group the last two terms:

$$= 4(7^k) + 3\bigl(7^k - 3^k\bigr)$$

The first term has a factor of $4$; the second is $3 \times P(k)$, divisible by $4$ by assumption. So the whole expression is divisible by $4$.

**Answer:** C
""",
                    "qk": False,
                },
                {
                    "label": """(c)""",
                    "order": 2,
                    "prompt": r"""Using induction, prove that $7^n - 3^n$ is divisible by **4** for all $n \in \mathbb{N}$.

Set out all three steps of the proof.""",
                    "answer": """$7^{k+1} - 3^{k+1} = 4(7^k) + 3(7^k - 3^k)$, both terms divisible by 4""",
                    "expected_format": r"""A full written proof in three steps: base case, assumption of $P(k)$, then the inductive step ending in a conclusion (e.g., $\therefore P(n)$ is true for all $n \in \mathbb{N}$).""",
                    "expected_type": """manual""",
                    "max_marks": 15,
                    "unlock": 2,
                    "scale": None,
                    "solution": r"""**Step 1 — Base case ($n = 1$):**

$$P(1) = 7^1 - 3^1 = 4$$

which is divisible by $4$, so $P(1)$ is true.

**Step 2 — Assume $P(k)$ is true:** assume $7^k - 3^k$ is divisible by $4$.

**Step 3 — Show $P(k+1)$ is true:**

$$P(k+1) = 7^{k+1} - 3^{k+1} = 7^k(7) - 3^k(3)$$

Split the $7$ into $(4 + 3)$ to introduce the divisor:

$$= 7^k(4 + 3) - 3^k(3) = 4(7^k) + 3(7^k) - 3(3^k)$$

$$= 4(7^k) + 3\bigl(7^k - 3^k\bigr)$$

- The first term, $4(7^k)$, contains a factor of $4$.
- The bracket $\bigl(7^k - 3^k\bigr)$ is $P(k)$, divisible by $4$ by assumption.

Both terms are divisible by $4$, so $P(k+1)$ is divisible by $4$.

$$\therefore\; P(k+1) \text{ is true if } P(k) \text{ is true}$$

$$\therefore\; P(n) \text{ is true for all } n \in \mathbb{N}. \qquad \textbf{Q.E.D.}$$""",
                    "qk": False,
                },
            ],
        },
        {
            "order": 2,
            "hint": """**The three steps:** (1) *Base case* — prove $P(n)$ for the smallest $n$. (2) *Hypothesis* — assume $P(k)$ is true. (3) *Inductive step* — use that assumption to prove $P(k+1)$. When $P(n)$ is a polynomial rather than a power, expand $P(k+1)$ in full, then split the expansion into $P(k)$ plus a remainder — and show the remainder has the divisor as a factor.""",
            "solution": None,
            "is_copyrighted": True,
            "is_exam_question": False,
            "is_quickkick_suitable": False,
            "parts": [
                {
                    "label": """(a)""",
                    "order": 0,
                    "prompt": r"""Let $P(n) = n^3 + 2n$, where $n \in \mathbb{N}$.

Verify the **base case** by evaluating $P(1)$.""",
                    "answer": """3""",
                    "expected_format": """Single whole number (e.g., 8 or 15)""",
                    "expected_type": """numeric""",
                    "max_marks": 5,
                    "unlock": 2,
                    "scale": None,
                    "solution": r"""**Step 1:** Substitute $n = 1$ into $P(n) = n^3 + 2n$.

$$P(1) = 1^3 + 2(1) = 1 + 2 = 3$$

**Step 2:** Since $3 = 3 \times 1$, $P(1)$ is divisible by $3$.

So the base case holds.

**Answer:** $3$""",
                    "qk": False,
                },
                {
                    "label": """(b)""",
                    "order": 1,
                    "prompt": r"""Expanding $P(k+1) = (k+1)^3 + 2(k+1)$ gives $k^3 + 3k^2 + 5k + 3$.

Which regrouping of this expression shows that $P(k+1)$ is divisible by **3**, given that $k^3 + 2k$ is divisible by **3**?

**(A)** $\bigl(k^3 + 2k\bigr) + 3k^2 + 3k$

**(B)** $\bigl(k^3 + 2k\bigr) + 3\bigl(k^2 + k + 1\bigr)$

**(C)** $\bigl(k^3 + 2k\bigr) + \bigl(3k^2 + 5k + 3\bigr)$

**(D)** $3\bigl(k^3 + 2k\bigr) + \bigl(k^2 + k + 1\bigr)$

**Format your answer as:** Answer: [A/B/C/D]""",
                    "answer": """B""",
                    "expected_format": """Single letter (e.g., C or D)""",
                    "expected_type": """multi""",
                    "max_marks": 10,
                    "unlock": 2,
                    "scale": None,
                    "solution": r"""**Step 1:** Expand fully:

$$(k+1)^3 + 2(k+1) = k^3 + 3k^2 + 3k + 1 + 2k + 2 = k^3 + 3k^2 + 5k + 3$$

**Step 2:** Pull out the terms that make up $P(k) = k^3 + 2k$:

$$= \bigl(k^3 + 2k\bigr) + \bigl(3k^2 + 3k + 3\bigr)$$

**Step 3:** Factor $3$ out of the remainder:

$$= \bigl(k^3 + 2k\bigr) + 3\bigl(k^2 + k + 1\bigr)$$

Option **B** is short by $3$, and option **C** leaves the remainder unfactored, so neither shows the divisibility.

**Answer:** B
""",
                    "qk": False,
                },
                {
                    "label": """(c)""",
                    "order": 2,
                    "prompt": r"""Using induction, prove that $n^3 + 2n$ is divisible by **3** for all $n \in \mathbb{N}$.

Set out all three steps of the proof.""",
                    "answer": """$P(k+1) = (k^3 + 2k) + 3(k^2 + k + 1)$, both terms divisible by 3""",
                    "expected_format": r"""A full written proof in three steps: base case, assumption of $P(k)$, then the inductive step ending in a conclusion (e.g., $\therefore P(n)$ is true for all $n \in \mathbb{N}$).""",
                    "expected_type": """manual""",
                    "max_marks": 15,
                    "unlock": 2,
                    "scale": None,
                    "solution": r"""**Step 1 — Base case ($n = 1$):**

$$P(1) = 1^3 + 2(1) = 3$$

which is divisible by $3$, so $P(1)$ is true.

**Step 2 — Assume $P(k)$ is true:** assume $k^3 + 2k$ is divisible by $3$.

**Step 3 — Show $P(k+1)$ is true:**

$$P(k+1) = (k+1)^3 + 2(k+1)$$

Expand:

$$= k^3 + 3k^2 + 3k + 1 + 2k + 2 = k^3 + 3k^2 + 5k + 3$$

Regroup so that $P(k)$ appears:

$$= \bigl(k^3 + 2k\bigr) + \bigl(3k^2 + 3k + 3\bigr) = \bigl(k^3 + 2k\bigr) + 3\bigl(k^2 + k + 1\bigr)$$

- The bracket $\bigl(k^3 + 2k\bigr)$ is $P(k)$, divisible by $3$ by assumption.
- The term $3\bigl(k^2 + k + 1\bigr)$ has a factor of $3$.

Both terms are divisible by $3$, so $P(k+1)$ is divisible by $3$.

$$\therefore\; P(k+1) \text{ is true if } P(k) \text{ is true}$$

$$\therefore\; P(n) \text{ is true for all } n \in \mathbb{N}. \qquad \textbf{Q.E.D.}$$""",
                    "qk": False,
                },
            ],
        },
        {
            "order": 3,
            "hint": """**The three steps:** (1) *Base case* — prove $P(n)$ for the smallest $n$. (2) *Hypothesis* — assume $P(k)$ is true. (3) *Inductive step* — use that assumption to prove $P(k+1)$. When $P(n)$ mixes a power with a linear term, multiply $P(k)$ by the base of the power, then correct the leftover linear terms — the correction should come out as a multiple of the divisor.""",
            "solution": None,
            "is_copyrighted": True,
            "is_exam_question": False,
            "is_quickkick_suitable": False,
            "parts": [
                {
                    "label": """(a)""",
                    "order": 0,
                    "prompt": r"""Let $P(n) = 4^n + 6n - 1$, where $n \in \mathbb{N}$.

Verify the **base case** by evaluating $P(1)$.""",
                    "answer": """9""",
                    "expected_format": """Single whole number (e.g., 7 or 21)""",
                    "expected_type": """numeric""",
                    "max_marks": 5,
                    "unlock": 2,
                    "scale": None,
                    "solution": r"""**Step 1:** Substitute $n = 1$ into $P(n) = 4^n + 6n - 1$.

$$P(1) = 4^1 + 6(1) - 1 = 4 + 6 - 1 = 9$$

**Step 2:** Since $9 = 9 \times 1$, $P(1)$ is divisible by $9$.

So the base case holds.

**Answer:** $9$""",
                    "qk": False,
                },
                {
                    "label": """(b)""",
                    "order": 1,
                    "prompt": r"""In the inductive step you must show that

$$P(k+1) = 4^{k+1} + 6(k+1) - 1 = 4(4^k) + 6k + 5$$

is divisible by **9**, given that $4^k + 6k - 1$ is divisible by **9**.

Which regrouping shows this?

**(A)** $4\bigl(4^k + 6k - 1\bigr) - 9(2k + 1)$

**(B)** $4\bigl(4^k + 6k - 1\bigr) + 9(2k - 1)$

**(C)** $9\bigl(4^k + 6k - 1\bigr) - 4(2k - 1)$

**(D)** $4\bigl(4^k + 6k - 1\bigr) - 9(2k - 1)$

**Format your answer as:** Answer: [A/B/C/D]""",
                    "answer": """D""",
                    "expected_format": """Single letter (e.g., B or C)""",
                    "expected_type": """multi""",
                    "max_marks": 10,
                    "unlock": 2,
                    "scale": None,
                    "solution": r"""**Step 1:** To make $P(k)$ appear, multiply it by $4$ — that produces the $4(4^k)$ we need:

$$4\bigl(4^k + 6k - 1\bigr) = 4(4^k) + 24k - 4$$

**Step 2:** Compare with the target $4(4^k) + 6k + 5$. The powers of $4$ match, so find the correction:

$$\bigl(6k + 5\bigr) - \bigl(24k - 4\bigr) = -18k + 9 = -9(2k - 1)$$

**Step 3:** Therefore

$$P(k+1) = 4\bigl(4^k + 6k - 1\bigr) - 9(2k - 1)$$

- The first term is $4 \times P(k)$, divisible by $9$ by assumption.
- The second term has a factor of $9$.

**Answer:** D
""",
                    "qk": False,
                },
                {
                    "label": """(c)""",
                    "order": 2,
                    "prompt": r"""Using induction, prove that $4^n + 6n - 1$ is divisible by **9** for all $n \in \mathbb{N}$.

Set out all three steps of the proof.""",
                    "answer": """$P(k+1) = 4(4^k + 6k - 1) - 9(2k - 1)$, both terms divisible by 9""",
                    "expected_format": r"""A full written proof in three steps: base case, assumption of $P(k)$, then the inductive step ending in a conclusion (e.g., $\therefore P(n)$ is true for all $n \in \mathbb{N}$).""",
                    "expected_type": """manual""",
                    "max_marks": 15,
                    "unlock": 2,
                    "scale": None,
                    "solution": r"""**Step 1 — Base case ($n = 1$):**

$$P(1) = 4^1 + 6(1) - 1 = 9$$

which is divisible by $9$, so $P(1)$ is true.

**Step 2 — Assume $P(k)$ is true:** assume $4^k + 6k - 1$ is divisible by $9$.

**Step 3 — Show $P(k+1)$ is true:**

$$P(k+1) = 4^{k+1} + 6(k+1) - 1 = 4(4^k) + 6k + 5$$

To make $P(k)$ appear, note that $4\bigl(4^k + 6k - 1\bigr) = 4(4^k) + 24k - 4$. Write $P(k+1)$ using this:

$$P(k+1) = \underbrace{4\bigl(4^k + 6k - 1\bigr)}_{= \,4(4^k) + 24k - 4} - 18k + 9$$

$$= 4\bigl(4^k + 6k - 1\bigr) - 9(2k - 1)$$

- The first term is $4 \times P(k)$, divisible by $9$ by assumption.
- The second term, $-9(2k - 1)$, contains a factor of $9$.

Both terms are divisible by $9$, so $P(k+1)$ is divisible by $9$.

$$\therefore\; P(k+1) \text{ is true if } P(k) \text{ is true}$$

$$\therefore\; P(n) \text{ is true for all } n \in \mathbb{N}. \qquad \textbf{Q.E.D.}$$""",
                    "qk": False,
                },
            ],
        },
    ]),
    ("""Series""", 2, [
        {
            "order": 1,
            "hint": """**The three steps:** (1) *Base case* — prove $P(n)$ for the smallest $n$. (2) *Hypothesis* — assume $P(k)$ is true. (3) *Inductive step* — use that assumption to prove $P(k+1)$. For a summation identity, add the $(k+1)$-th term to both sides of $P(k)$, then simplify the right-hand side until it matches the original formula with $n$ replaced by $k+1$.""",
            "solution": None,
            "is_copyrighted": True,
            "is_exam_question": False,
            "is_quickkick_suitable": False,
            "parts": [
                {
                    "label": """(a)""",
                    "order": 0,
                    "prompt": r"""Consider the statement

$$1 + 4 + 7 + \cdots + (3n - 2) = \frac{n(3n - 1)}{2}$$

Verify the **base case** by evaluating the right-hand side at $n = 1$.""",
                    "answer": """1""",
                    "expected_format": """Single whole number (e.g., 5 or 12)""",
                    "expected_type": """numeric""",
                    "max_marks": 5,
                    "unlock": 2,
                    "scale": None,
                    "solution": r"""**Step 1:** Substitute $n = 1$ into the right-hand side.

$$\frac{1\bigl(3(1) - 1\bigr)}{2} = \frac{1(2)}{2} = 1$$

**Step 2:** Compare with the left-hand side, which at $n = 1$ is just the first term:

$$3(1) - 2 = 1$$

Both sides equal $1$, so $P(1)$ is true.

**Answer:** $1$""",
                    "qk": False,
                },
                {
                    "label": """(b)""",
                    "order": 1,
                    "prompt": r"""To move from $P(k)$ to $P(k+1)$, one more term is added to the left-hand side of

$$1 + 4 + 7 + \cdots + (3k - 2) = \frac{k(3k - 1)}{2}$$

What is the $(k+1)$-th term of the series?

**(A)** $3k + 1$

**(B)** $3k - 2$

**(C)** $3k + 4$

**(D)** $3k - 1$

**Format your answer as:** Answer: [A/B/C/D]""",
                    "answer": """A""",
                    "expected_format": """Single letter (e.g., B or D)""",
                    "expected_type": """multi""",
                    "max_marks": 10,
                    "unlock": 2,
                    "scale": None,
                    "solution": """**Step 1:** The general term of the series is $3n - 2$.

**Step 2:** Replace $n$ with $k + 1$:

$$3(k + 1) - 2 = 3k + 3 - 2 = 3k + 1$$

Option **B** is the $k$-th term, not the $(k+1)$-th.

**Answer:** A""",
                    "qk": False,
                },
                {
                    "label": """(c)""",
                    "order": 2,
                    "prompt": r"""Using induction, prove that

$$1 + 4 + 7 + \cdots + (3n - 2) = \frac{n(3n - 1)}{2}$$

for all $n \in \mathbb{N}$. Set out all three steps of the proof.""",
                    "answer": r"""$\frac{k(3k-1)}{2} + (3k+1) = \frac{(k+1)(3k+2)}{2}$""",
                    "expected_format": r"""A full written proof in three steps: base case, assumption of $P(k)$, then the inductive step ending in a conclusion (e.g., $\therefore P(n)$ is true for all $n \in \mathbb{N}$).""",
                    "expected_type": """manual""",
                    "max_marks": 15,
                    "unlock": 2,
                    "scale": None,
                    "solution": r"""**Step 1 — Base case ($n = 1$):** the left-hand side has just the first term, so

$$\text{LHS} = 1, \qquad \text{RHS} = \frac{1(3 - 1)}{2} = 1. \quad\checkmark$$

So $P(1)$ is true.

**Step 2 — Assume $P(k)$ is true:**

$$1 + 4 + 7 + \cdots + (3k - 2) = \frac{k(3k - 1)}{2}$$

**Step 3 — Show $P(k+1)$ is true:** we must show

$$1 + 4 + \cdots + (3k - 2) + (3k + 1) = \frac{(k+1)\bigl(3(k+1) - 1\bigr)}{2} = \frac{(k+1)(3k + 2)}{2}$$

Replace the first $k$ terms using the inductive hypothesis:

$$\frac{k(3k - 1)}{2} + (3k + 1)$$

Put over a common denominator:

$$= \frac{k(3k - 1) + 2(3k + 1)}{2} = \frac{3k^2 - k + 6k + 2}{2} = \frac{3k^2 + 5k + 2}{2}$$

Factor the numerator:

$$= \frac{(k + 1)(3k + 2)}{2} \quad\checkmark$$

This is the right-hand side with $n$ replaced by $k+1$.

$$\therefore\; P(k+1) \text{ is true if } P(k) \text{ is true}$$

$$\therefore\; P(n) \text{ is true for all } n \in \mathbb{N}. \qquad \textbf{Q.E.D.}$$""",
                    "qk": False,
                },
            ],
        },
        {
            "order": 2,
            "hint": """**The three steps:** (1) *Base case* — prove $P(n)$ for the smallest $n$. (2) *Hypothesis* — assume $P(k)$ is true. (3) *Inductive step* — use that assumption to prove $P(k+1)$. When the right-hand side is a product, take out the common factor after adding the $(k+1)$-th term — here $(k+1)$ is a factor of both pieces — then factorise the quadratic that is left.""",
            "solution": None,
            "is_copyrighted": True,
            "is_exam_question": False,
            "is_quickkick_suitable": False,
            "parts": [
                {
                    "label": """(a)""",
                    "order": 0,
                    "prompt": r"""Consider the statement

$$\sum_{r=1}^{n} r^2 = 1^2 + 2^2 + 3^2 + \cdots + n^2 = \frac{n(n + 1)(2n + 1)}{6}$$

Verify the **base case** by evaluating the right-hand side at $n = 1$.""",
                    "answer": """1""",
                    "expected_format": """Single whole number (e.g., 4 or 9)""",
                    "expected_type": """numeric""",
                    "max_marks": 5,
                    "unlock": 2,
                    "scale": None,
                    "solution": r"""**Step 1:** Substitute $n = 1$ into the right-hand side.

$$\frac{1(1 + 1)\bigl(2(1) + 1\bigr)}{6} = \frac{1 \times 2 \times 3}{6} = \frac{6}{6} = 1$$

**Step 2:** The left-hand side at $n = 1$ is $1^2 = 1$.

Both sides equal $1$, so $P(1)$ is true.

**Answer:** $1$""",
                    "qk": False,
                },
                {
                    "label": """(b)""",
                    "order": 1,
                    "prompt": r"""Assuming $P(k)$, adding the $(k+1)$-th term gives

$$\frac{k(k + 1)(2k + 1)}{6} + (k + 1)^2$$

Which of the following correctly takes out the common factor?

**(A)** $\dfrac{k + 1}{6}\Bigl[k(2k + 1) + 6\Bigr]$

**(B)** $\dfrac{k + 1}{6}\Bigl[k(2k + 1) + (k + 1)\Bigr]$

**(C)** $\dfrac{k}{6}\Bigl[(k + 1)(2k + 1) + 6(k + 1)\Bigr]$

**(D)** $\dfrac{k + 1}{6}\Bigl[k(2k + 1) + 6(k + 1)\Bigr]$

**Format your answer as:** Answer: [A/B/C/D]""",
                    "answer": """D""",
                    "expected_format": """Single letter (e.g., C or D)""",
                    "expected_type": """multi""",
                    "max_marks": 10,
                    "unlock": 2,
                    "scale": None,
                    "solution": r"""**Step 1:** Put both terms over the denominator $6$:

$$\frac{k(k + 1)(2k + 1)}{6} + \frac{6(k + 1)^2}{6} = \frac{k(k + 1)(2k + 1) + 6(k + 1)^2}{6}$$

**Step 2:** Both terms in the numerator contain $(k + 1)$, so take it out:

$$= \frac{(k + 1)\Bigl[k(2k + 1) + 6(k + 1)\Bigr]}{6}$$

Option **B** forgets to multiply $(k+1)^2$ by $6$ when forming the common denominator, and **D** drops a factor of $(k+1)$.

**Answer:** D
""",
                    "qk": False,
                },
                {
                    "label": """(c)""",
                    "order": 2,
                    "prompt": r"""Using induction, prove that

$$1^2 + 2^2 + 3^2 + \cdots + n^2 = \frac{n(n + 1)(2n + 1)}{6}$$

for all $n \in \mathbb{N}$. Set out all three steps of the proof.""",
                    "answer": r"""$\frac{k(k+1)(2k+1)}{6} + (k+1)^2 = \frac{(k+1)(k+2)(2k+3)}{6}$""",
                    "expected_format": r"""A full written proof in three steps: base case, assumption of $P(k)$, then the inductive step ending in a conclusion (e.g., $\therefore P(n)$ is true for all $n \in \mathbb{N}$).""",
                    "expected_type": """manual""",
                    "max_marks": 15,
                    "unlock": 2,
                    "scale": None,
                    "solution": r"""**Step 1 — Base case ($n = 1$):**

$$\text{LHS} = 1^2 = 1, \qquad \text{RHS} = \frac{1(2)(3)}{6} = 1. \quad\checkmark$$

So $P(1)$ is true.

**Step 2 — Assume $P(k)$ is true:**

$$1^2 + 2^2 + \cdots + k^2 = \frac{k(k + 1)(2k + 1)}{6}$$

**Step 3 — Show $P(k+1)$ is true:** we must show

$$1^2 + 2^2 + \cdots + k^2 + (k + 1)^2 = \frac{(k + 1)(k + 2)(2k + 3)}{6}$$

Replace the first $k$ terms using the inductive hypothesis:

$$\frac{k(k + 1)(2k + 1)}{6} + (k + 1)^2 = \frac{k(k + 1)(2k + 1) + 6(k + 1)^2}{6}$$

Take out the common factor $(k + 1)$:

$$= \frac{(k + 1)\Bigl[k(2k + 1) + 6(k + 1)\Bigr]}{6} = \frac{(k + 1)\bigl(2k^2 + k + 6k + 6\bigr)}{6}$$

$$= \frac{(k + 1)\bigl(2k^2 + 7k + 6\bigr)}{6}$$

Factorise the quadratic:

$$= \frac{(k + 1)(k + 2)(2k + 3)}{6} \quad\checkmark$$

Since $2(k+1) + 1 = 2k + 3$ and $(k+1) + 1 = k + 2$, this is the right-hand side with $n$ replaced by $k+1$.

$$\therefore\; P(k+1) \text{ is true if } P(k) \text{ is true}$$

$$\therefore\; P(n) \text{ is true for all } n \in \mathbb{N}. \qquad \textbf{Q.E.D.}$$""",
                    "qk": False,
                },
            ],
        },
        {
            "order": 3,
            "hint": r"""**The three steps:** (1) *Base case* — prove $P(n)$ for the smallest $n$. (2) *Hypothesis* — assume $P(k)$ is true. (3) *Inductive step* — use that assumption to prove $P(k+1)$. For a series of fractions, add the $(k+1)$-th term to $\frac{k}{k+1}$ over a common denominator. The numerator will factorise and cancel with the denominator.""",
            "solution": None,
            "is_copyrighted": True,
            "is_exam_question": False,
            "is_quickkick_suitable": False,
            "parts": [
                {
                    "label": """(a)""",
                    "order": 0,
                    "prompt": r"""Consider the statement

$$\frac{1}{1 \times 2} + \frac{1}{2 \times 3} + \frac{1}{3 \times 4} + \cdots + \frac{1}{n(n + 1)} = \frac{n}{n + 1}$$

Verify the **base case** by evaluating the right-hand side at $n = 1$.""",
                    "answer": """1/2""",
                    "expected_format": r"""Fraction in simplest form, typed with a slash (e.g., 2/7 for $\frac{2}{7}$)""",
                    "expected_type": """numeric""",
                    "max_marks": 5,
                    "unlock": 2,
                    "scale": None,
                    "solution": r"""**Step 1:** Substitute $n = 1$ into the right-hand side.

$$\frac{1}{1 + 1} = \frac{1}{2}$$

**Step 2:** The left-hand side at $n = 1$ is the first term only:

$$\frac{1}{1 \times 2} = \frac{1}{2}$$

Both sides equal $\frac{1}{2}$, so $P(1)$ is true.

**Answer:** $\frac{1}{2}$""",
                    "qk": False,
                },
                {
                    "label": """(b)""",
                    "order": 1,
                    "prompt": r"""Assuming $P(k)$, adding the $(k+1)$-th term gives

$$\frac{k}{k + 1} + \frac{1}{(k + 1)(k + 2)}$$

Simplify this to a single fraction in its simplest form.

**(A)** $\dfrac{k}{k + 2}$

**(B)** $\dfrac{k + 1}{k + 2}$

**(C)** $\dfrac{k^2 + 1}{(k + 1)(k + 2)}$

**(D)** $\dfrac{1}{k + 2}$

**Format your answer as:** Answer: [A/B/C/D]""",
                    "answer": """B""",
                    "expected_format": """Single letter (e.g., B or D)""",
                    "expected_type": """multi""",
                    "max_marks": 10,
                    "unlock": 2,
                    "scale": None,
                    "solution": r"""**Step 1:** The common denominator is $(k + 1)(k + 2)$:

$$\frac{k(k + 2)}{(k + 1)(k + 2)} + \frac{1}{(k + 1)(k + 2)} = \frac{k(k + 2) + 1}{(k + 1)(k + 2)}$$

**Step 2:** Expand and factorise the numerator:

$$k^2 + 2k + 1 = (k + 1)^2$$

**Step 3:** Cancel the common factor $(k + 1)$:

$$\frac{(k + 1)^2}{(k + 1)(k + 2)} = \frac{k + 1}{k + 2}$$

Option **C** stops before spotting that the numerator is a perfect square.

**Answer:** B
""",
                    "qk": False,
                },
                {
                    "label": """(c)""",
                    "order": 2,
                    "prompt": r"""Using induction, prove that

$$\frac{1}{1 \times 2} + \frac{1}{2 \times 3} + \cdots + \frac{1}{n(n + 1)} = \frac{n}{n + 1}$$

for all $n \in \mathbb{N}$. Set out all three steps of the proof.""",
                    "answer": r"""$\frac{k}{k+1} + \frac{1}{(k+1)(k+2)} = \frac{k+1}{k+2}$""",
                    "expected_format": r"""A full written proof in three steps: base case, assumption of $P(k)$, then the inductive step ending in a conclusion (e.g., $\therefore P(n)$ is true for all $n \in \mathbb{N}$).""",
                    "expected_type": """manual""",
                    "max_marks": 15,
                    "unlock": 2,
                    "scale": None,
                    "solution": r"""**Step 1 — Base case ($n = 1$):**

$$\text{LHS} = \frac{1}{1 \times 2} = \frac{1}{2}, \qquad \text{RHS} = \frac{1}{1 + 1} = \frac{1}{2}. \quad\checkmark$$

So $P(1)$ is true.

**Step 2 — Assume $P(k)$ is true:**

$$\frac{1}{1 \times 2} + \frac{1}{2 \times 3} + \cdots + \frac{1}{k(k + 1)} = \frac{k}{k + 1}$$

**Step 3 — Show $P(k+1)$ is true:** the $(k+1)$-th term is $\dfrac{1}{(k + 1)(k + 2)}$, so we must show

$$\frac{1}{1 \times 2} + \cdots + \frac{1}{k(k + 1)} + \frac{1}{(k + 1)(k + 2)} = \frac{k + 1}{k + 2}$$

Replace the first $k$ terms using the inductive hypothesis:

$$\frac{k}{k + 1} + \frac{1}{(k + 1)(k + 2)}$$

Use the common denominator $(k + 1)(k + 2)$:

$$= \frac{k(k + 2) + 1}{(k + 1)(k + 2)} = \frac{k^2 + 2k + 1}{(k + 1)(k + 2)}$$

The numerator is a perfect square:

$$= \frac{(k + 1)^2}{(k + 1)(k + 2)} = \frac{k + 1}{k + 2} \quad\checkmark$$

This is the right-hand side with $n$ replaced by $k+1$.

$$\therefore\; P(k+1) \text{ is true if } P(k) \text{ is true}$$

$$\therefore\; P(n) \text{ is true for all } n \in \mathbb{N}. \qquad \textbf{Q.E.D.}$$""",
                    "qk": False,
                },
            ],
        },
    ]),
    ("""Inequalities""", 3, [
        {
            "order": 1,
            "hint": """**The three steps:** (1) *Base case* — prove $P(n)$ for the smallest $n$. (2) *Hypothesis* — assume $P(k)$ is true. (3) *Inductive step* — use that assumption to prove $P(k+1)$. For inequalities the base case is usually **not** $n = 1$ — check the smallest $n$ for which the statement holds. In the inductive step, use $P(k)$ to replace one side, then reduce to a statement that is clearly true.""",
            "solution": None,
            "is_copyrighted": True,
            "is_exam_question": False,
            "is_quickkick_suitable": False,
            "parts": [
                {
                    "label": """(a)""",
                    "order": 0,
                    "prompt": r"""The statement $2^n > n^2$ is to be proved for all $n \geq 5$, $n \in \mathbb{N}$.

To see why the proof cannot start at $n = 4$, evaluate **both** $2^4$ and $4^2$. State their common value.""",
                    "answer": """16""",
                    "expected_format": """Single whole number (e.g., 25 or 64)""",
                    "expected_type": """numeric""",
                    "max_marks": 5,
                    "unlock": 2,
                    "scale": None,
                    "solution": r"""**Step 1:** Evaluate each side at $n = 4$:

$$2^4 = 16, \qquad 4^2 = 16$$

**Step 2:** Since $16 > 16$ is **false**, the statement fails at $n = 4$ — the two sides are equal, not strictly greater.

**Step 3:** Check $n = 5$:

$$2^5 = 32, \qquad 5^2 = 25, \qquad 32 > 25 \quad\checkmark$$

So $n = 5$ is the correct base case.

**Answer:** $16$""",
                    "qk": False,
                },
                {
                    "label": """(b)""",
                    "order": 1,
                    "prompt": r"""Assume $2^k > k^2$ for some $k \geq 5$. Multiplying both sides by $2$ gives

$$2^{k+1} = 2\bigl(2^k\bigr) > 2k^2$$

What remains to be shown to complete the inductive step?

**(A)** $k^2 > (k + 1)^2$ for $k \geq 5$

**(B)** $2k^2 > 2(k + 1)^2$ for $k \geq 5$

**(C)** $2k^2 \geq (k + 1)^2$ for $k \geq 5$

**(D)** $2k^2 \geq k^2 + 1$ for $k \geq 5$

**Format your answer as:** Answer: [A/B/C/D]""",
                    "answer": """C""",
                    "expected_format": """Single letter (e.g., B or C)""",
                    "expected_type": """multi""",
                    "max_marks": 10,
                    "unlock": 2,
                    "scale": None,
                    "solution": r"""**Step 1:** The goal of the inductive step is $2^{k+1} > (k + 1)^2$.

**Step 2:** We already have $2^{k+1} > 2k^2$. Chaining the two inequalities, it is enough to show

$$2k^2 \geq (k + 1)^2$$

because then $2^{k+1} > 2k^2 \geq (k+1)^2$.

**Step 3:** Option **C** is false for every $k$, and option **D** is true but too weak — it does not reach $(k+1)^2$.

**Answer:** C
""",
                    "qk": False,
                },
                {
                    "label": """(c)""",
                    "order": 2,
                    "prompt": r"""Using induction, prove that $2^n > n^2$ for all $n \geq 5$, $n \in \mathbb{N}$.

Set out all three steps of the proof.""",
                    "answer": r"""Base $n=5$: $32 > 25$; step reduces to $k^2 - 2k - 1 > 0$, true for $k \geq 5$""",
                    "expected_format": r"""A full written proof in three steps: base case, assumption of $P(k)$, then the inductive step ending in a conclusion (e.g., $\therefore P(n)$ is true for all $n \in \mathbb{N}$).""",
                    "expected_type": """manual""",
                    "max_marks": 15,
                    "unlock": 2,
                    "scale": None,
                    "solution": r"""**Step 1 — Base case ($n = 5$):**

$$2^5 = 32, \qquad 5^2 = 25$$

and $32 > 25$, so $P(5)$ is true.

**Step 2 — Assume $P(k)$ is true** for some $k \geq 5$:

$$2^k > k^2$$

**Step 3 — Show $P(k+1)$ is true:** we must show $2^{k+1} > (k + 1)^2$.

Multiply the inductive hypothesis by $2$:

$$2^{k+1} = 2\bigl(2^k\bigr) > 2k^2$$

So it is enough to show that $2k^2 \geq (k + 1)^2$. Expand:

$$2k^2 \geq k^2 + 2k + 1 \;\Longleftrightarrow\; k^2 - 2k - 1 \geq 0$$

For $k \geq 5$:

$$k^2 - 2k - 1 = k(k - 2) - 1 \geq 5(3) - 1 = 14 > 0 \quad\checkmark$$

Therefore $2k^2 > (k+1)^2$, and chaining the inequalities:

$$2^{k+1} > 2k^2 > (k + 1)^2$$

$$\therefore\; P(k+1) \text{ is true if } P(k) \text{ is true}$$

$$\therefore\; P(n) \text{ is true for all } n \geq 5,\; n \in \mathbb{N}. \qquad \textbf{Q.E.D.}$$""",
                    "qk": False,
                },
            ],
        },
        {
            "order": 2,
            "hint": r"""**The three steps:** (1) *Base case* — prove $P(n)$ for the smallest $n$. (2) *Hypothesis* — assume $P(k)$ is true. (3) *Inductive step* — use that assumption to prove $P(k+1)$. Where the inequality is $\geq$, the base case may hold with equality — that is still fine. In the inductive step, multiply $P(k)$ by the base of the power, then show the result is at least the target.""",
            "solution": None,
            "is_copyrighted": True,
            "is_exam_question": False,
            "is_quickkick_suitable": False,
            "parts": [
                {
                    "label": """(a)""",
                    "order": 0,
                    "prompt": r"""The statement $3^n \geq 1 + 2n$ is to be proved for all $n \in \mathbb{N}$.

Verify the **base case** by evaluating the right-hand side, $1 + 2n$, at $n = 1$.""",
                    "answer": """3""",
                    "expected_format": """Single whole number (e.g., 5 or 9)""",
                    "expected_type": """numeric""",
                    "max_marks": 5,
                    "unlock": 2,
                    "scale": None,
                    "solution": r"""**Step 1:** Substitute $n = 1$ into the right-hand side:

$$1 + 2(1) = 3$$

**Step 2:** The left-hand side is $3^1 = 3$.

**Step 3:** Since $3 \geq 3$ is true (equality is allowed by $\geq$), $P(1)$ is true.

**Answer:** $3$""",
                    "qk": False,
                },
                {
                    "label": """(b)""",
                    "order": 1,
                    "prompt": r"""Assume $3^k \geq 1 + 2k$ for some $k \in \mathbb{N}$. Multiplying both sides by $3$ gives

$$3^{k+1} \geq 3(1 + 2k) = 6k + 3$$

The target for $P(k+1)$ is $1 + 2(k + 1) = 2k + 3$. Which inequality completes the proof?

**(A)** $6k + 3 \geq 2k + 3$

**(B)** $6k + 3 \geq 6k + 5$

**(C)** $6k + 3 \leq 2k + 3$

**(D)** $3k + 1 \geq 2k + 3$

**Format your answer as:** Answer: [A/B/C/D]""",
                    "answer": """A""",
                    "expected_format": """Single letter (e.g., C or D)""",
                    "expected_type": """multi""",
                    "max_marks": 10,
                    "unlock": 2,
                    "scale": None,
                    "solution": r"""**Step 1:** We have $3^{k+1} \geq 6k + 3$ and we want $3^{k+1} \geq 2k + 3$.

**Step 2:** It is enough to show $6k + 3 \geq 2k + 3$, since then

$$3^{k+1} \geq 6k + 3 \geq 2k + 3$$

**Step 3:** Check that it is true: subtracting $2k + 3$ from both sides gives $4k \geq 0$, which holds for every $k \in \mathbb{N}$.

**Answer:** A""",
                    "qk": False,
                },
                {
                    "label": """(c)""",
                    "order": 2,
                    "prompt": r"""Using induction, prove that $3^n \geq 1 + 2n$ for all $n \in \mathbb{N}$.

Set out all three steps of the proof.""",
                    "answer": r"""Base $n=1$: $3 \geq 3$; step reduces to $4k \geq 0$, true for all $k \in \mathbb{N}$""",
                    "expected_format": r"""A full written proof in three steps: base case, assumption of $P(k)$, then the inductive step ending in a conclusion (e.g., $\therefore P(n)$ is true for all $n \in \mathbb{N}$).""",
                    "expected_type": """manual""",
                    "max_marks": 15,
                    "unlock": 2,
                    "scale": None,
                    "solution": r"""**Step 1 — Base case ($n = 1$):**

$$\text{LHS} = 3^1 = 3, \qquad \text{RHS} = 1 + 2(1) = 3$$

and $3 \geq 3$, so $P(1)$ is true. (Equality is permitted because the inequality is $\geq$.)

**Step 2 — Assume $P(k)$ is true:**

$$3^k \geq 1 + 2k$$

**Step 3 — Show $P(k+1)$ is true:** we must show

$$3^{k+1} \geq 1 + 2(k + 1) = 2k + 3$$

Multiply the inductive hypothesis by $3$ (positive, so the inequality is preserved):

$$3^{k+1} = 3\bigl(3^k\bigr) \geq 3(1 + 2k) = 6k + 3$$

Now compare $6k + 3$ with the target $2k + 3$:

$$6k + 3 - (2k + 3) = 4k \geq 0 \quad \text{for all } k \in \mathbb{N}$$

so $6k + 3 \geq 2k + 3$. Chaining the inequalities:

$$3^{k+1} \geq 6k + 3 \geq 2k + 3 \quad\checkmark$$

$$\therefore\; P(k+1) \text{ is true if } P(k) \text{ is true}$$

$$\therefore\; P(n) \text{ is true for all } n \in \mathbb{N}. \qquad \textbf{Q.E.D.}$$""",
                    "qk": False,
                },
            ],
        },
        {
            "order": 3,
            "hint": r"""**The three steps:** (1) *Base case* — prove $P(n)$ for the smallest $n$. (2) *Hypothesis* — assume $P(k)$ is true. (3) *Inductive step* — use that assumption to prove $P(k+1)$. Remember $(k+1)! = (k+1) \times k!$ — this is what lets you multiply the inductive hypothesis by $(k+1)$. Then compare the result with the target and show the leftover factor is big enough.""",
            "solution": None,
            "is_copyrighted": True,
            "is_exam_question": False,
            "is_quickkick_suitable": False,
            "parts": [
                {
                    "label": """(a)""",
                    "order": 0,
                    "prompt": r"""The statement $n! > 2^n$ is to be proved for all $n \geq 4$, $n \in \mathbb{N}$.

Verify the **base case** by evaluating $4! - 2^4$.""",
                    "answer": """8""",
                    "expected_format": """Single whole number (e.g., 6 or 14)""",
                    "expected_type": """numeric""",
                    "max_marks": 5,
                    "unlock": 2,
                    "scale": None,
                    "solution": r"""**Step 1:** Evaluate each part:

$$4! = 4 \times 3 \times 2 \times 1 = 24, \qquad 2^4 = 16$$

**Step 2:** Subtract:

$$24 - 16 = 8$$

**Step 3:** Since the difference is positive, $4! > 2^4$ and the base case holds.

(At $n = 3$ it would fail: $3! = 6$ and $2^3 = 8$, so $6 > 8$ is false.)

**Answer:** $8$""",
                    "qk": False,
                },
                {
                    "label": """(b)""",
                    "order": 1,
                    "prompt": r"""Assume $k! > 2^k$ for some $k \geq 4$. Multiplying both sides by $(k + 1)$ gives

$$(k + 1)! > (k + 1)2^k$$

What remains to be shown to complete the inductive step?

**(A)** $(k + 1)2^k \geq 2^k$, which holds because $k + 1 \geq 1$

**(B)** $(k + 1)2^k \geq 2^{k+1}(k + 1)$, which holds because $k \geq 4$

**(C)** $(k + 1)2^k \leq 2^{k+1}$, which holds because $k + 1 \leq 2$

**(D)** $(k + 1)2^k \geq 2\bigl(2^k\bigr)$, which holds because $k + 1 > 2$ for $k \geq 4$

**Format your answer as:** Answer: [A/B/C/D]""",
                    "answer": """D""",
                    "expected_format": """Single letter (e.g., B or C)""",
                    "expected_type": """multi""",
                    "max_marks": 10,
                    "unlock": 2,
                    "scale": None,
                    "solution": r"""**Step 1:** The goal of the inductive step is $(k + 1)! > 2^{k+1}$.

**Step 2:** Note that $2^{k+1} = 2\bigl(2^k\bigr)$. So starting from $(k + 1)! > (k + 1)2^k$, it is enough to show

$$(k + 1)2^k \geq 2\bigl(2^k\bigr)$$

which is true precisely when $k + 1 \geq 2$. For $k \geq 4$ we have $k + 1 \geq 5 > 2$. $\checkmark$

**Step 3:** Option **D** is true but too weak — it only reaches $2^k$, not $2^{k+1}$.

**Answer:** D
""",
                    "qk": False,
                },
                {
                    "label": """(c)""",
                    "order": 2,
                    "prompt": r"""Using induction, prove that $n! > 2^n$ for all $n \geq 4$, $n \in \mathbb{N}$.

Set out all three steps of the proof.""",
                    "answer": r"""Base $n=4$: $24 > 16$; step uses $(k+1)! > (k+1)2^k \geq 2 \cdot 2^k = 2^{k+1}$ since $k+1 > 2$""",
                    "expected_format": r"""A full written proof in three steps: base case, assumption of $P(k)$, then the inductive step ending in a conclusion (e.g., $\therefore P(n)$ is true for all $n \in \mathbb{N}$).""",
                    "expected_type": """manual""",
                    "max_marks": 15,
                    "unlock": 2,
                    "scale": None,
                    "solution": r"""**Step 1 — Base case ($n = 4$):**

$$4! = 24, \qquad 2^4 = 16$$

and $24 > 16$, so $P(4)$ is true.

**Step 2 — Assume $P(k)$ is true** for some $k \geq 4$:

$$k! > 2^k$$

**Step 3 — Show $P(k+1)$ is true:** we must show $(k + 1)! > 2^{k+1}$.

Multiply the inductive hypothesis by $(k + 1)$, which is positive:

$$(k + 1) \times k! > (k + 1) \times 2^k$$

The left-hand side is $(k + 1)!$, so

$$(k + 1)! > (k + 1)2^k$$

Since $k \geq 4$, we have $k + 1 \geq 5 > 2$, and therefore

$$(k + 1)2^k > 2\bigl(2^k\bigr) = 2^{k+1}$$

Chaining the two inequalities:

$$(k + 1)! > (k + 1)2^k > 2^{k+1} \quad\checkmark$$

$$\therefore\; P(k+1) \text{ is true if } P(k) \text{ is true}$$

$$\therefore\; P(n) \text{ is true for all } n \geq 4,\; n \in \mathbb{N}. \qquad \textbf{Q.E.D.}$$""",
                    "qk": False,
                },
            ],
        },
    ]),
]


class Command(BaseCommand):
    help = "Add or update the Proof by Induction practice questions"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would change without writing anything",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        try:
            subject = Subject.objects.get(name=SUBJECT_NAME)
        except Subject.DoesNotExist:
            self.stderr.write(self.style.ERROR(
                f'No "{SUBJECT_NAME}" subject - run the core migrations first.'
            ))
            return

        with transaction.atomic():
            topic, created = Topic.objects.get_or_create(
                slug=TOPIC_SLUG,
                defaults={"name": TOPIC_NAME, "subject": subject, "paper": PAPER},
            )
            self.stdout.write(f'{"Created" if created else "Found"} topic "{topic.name}"')

            # An earlier hand-run may have left the topic without a subject or
            # paper, which hides it from every subject-filtered page.
            repairs = {}
            if topic.subject_id is None:
                repairs["subject"] = subject
            if not topic.paper:
                repairs["paper"] = PAPER
            if repairs:
                self.stdout.write(self.style.WARNING(
                    f"  repairing topic: {', '.join(sorted(repairs))}"
                ))
                if not dry_run:
                    for field, value in repairs.items():
                        setattr(topic, field, value)
                    topic.save(update_fields=list(repairs))

            questions = parts = 0
            for section_name, section_order, entries in QUESTIONS:
                section, _ = Section.objects.get_or_create(
                    topic=topic,
                    name=section_name,
                    defaults={"order": section_order},
                )
                self.stdout.write(f"  section {section.name}")

                for entry in entries:
                    if dry_run:
                        exists = Question.objects.filter(
                            topic=topic, section=section, order=entry["order"]
                        ).exists()
                        verb = "update" if exists else "create"
                        self.stdout.write(
                            f'    would {verb} question {entry["order"]} '
                            f'({len(entry["parts"])} parts)'
                        )
                        questions += 1
                        parts += len(entry["parts"])
                        continue

                    question, made = Question.objects.update_or_create(
                        topic=topic,
                        section=section,
                        order=entry["order"],
                        defaults={
                            "hint": entry["hint"],
                            "solution": entry["solution"],
                            "is_copyrighted": entry["is_copyrighted"],
                            "is_exam_question": entry["is_exam_question"],
                            "is_quickkick_suitable": entry["is_quickkick_suitable"],
                        },
                    )
                    questions += 1
                    self.stdout.write(
                        f'    {"created" if made else "updated"} question {question.order}'
                    )

                    for part in entry["parts"]:
                        QuestionPart.objects.update_or_create(
                            question=question,
                            label=part["label"],
                            defaults={
                                "prompt": part["prompt"],
                                "answer": part["answer"],
                                "expected_format": part["expected_format"],
                                "solution": part["solution"],
                                "expected_type": part["expected_type"],
                                "max_marks": part["max_marks"],
                                "order": part["order"],
                                "solution_unlock_after_attempts": part["unlock"],
                                "scale": part["scale"],
                                "is_quickkick_suitable": part["qk"],
                            },
                        )
                        parts += 1

            if dry_run:
                transaction.set_rollback(True)

        prefix = "Would touch" if dry_run else "Wrote"
        self.stdout.write(self.style.SUCCESS(
            f"\n{prefix} {questions} questions and {parts} parts."
        ))
