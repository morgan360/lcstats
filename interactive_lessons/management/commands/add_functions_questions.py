"""Add the Functions practice questions: seven Warm-up, seven Workout, six Stretch.

Content authored on local and replayed here so production gets exactly what was
tested. Idempotent: keyed on topic slug, section name and question order rather
than primary key, because ids differ between local and production. Re-running
updates in place and never duplicates.

Written to the learning outcomes of Active Maths 4, Chapter 6 (Functions), in
our own words and numbers: a function's unique output, domain and range,
composite functions, the shapes of linear, quadratic, cubic, exponential and
log graphs, graphical solutions of f(x) = k and f(x) = g(x), completed square
form, transformations, injective/surjective/bijective, and inverses. The three
existing "Composite Functions" questions are left as they are.

Answers are stored in forms the grader checks without GPT: plain numbers,
single letters for multiple choice, expressions it can compare algebraically,
and pairs of numbers. A pair is stored smallest first (or x first for a point)
and the format line says so, because mark_student_answer reads any
comma-separated answer as an interval: it compares only the first two numbers,
in order. For the same reason no answer here has three values.
Where a question asks for a particular form, the parts ask for the numbers in
it instead, because an algebraic check would also accept the expanded form.
Every answer was checked with SymPy (scripts/check_functions_answers.py).
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Subject
from interactive_lessons.models import Topic, Question, QuestionPart, Section

TOPIC_SLUG = "functions"
TOPIC_NAME = "Functions"
SUBJECT_NAME = "Maths"
PAPER = "p1"

NUM = "Number only (e.g., 7 or -2.5)"
NUMS = "Two numbers separated by a comma, smallest first (e.g., -2, 3)"
POINT = "Two numbers separated by a comma, x first (e.g., 3, -2)"
LETTER = "Single letter (e.g., B or D)"
EXPR = "An expression in $x$ (e.g., 3x^2 - 2x + 1)"


def part(label, order, prompt, answer, expected_type, expected_format, max_marks,
         solution):
    return {
        "label": label, "order": order, "prompt": prompt, "answer": answer,
        "expected_format": expected_format, "expected_type": expected_type,
        "max_marks": max_marks, "unlock": 2, "scale": None,
        "solution": solution, "qk": False,
    }


def question(order, hint, parts):
    return {
        "order": order, "hint": hint, "solution": None,
        "is_copyrighted": True, "is_exam_question": False,
        "is_quickkick_suitable": False, "parts": parts,
    }


# (section name, section order, [questions])
QUESTIONS = [
    ("""Warm-up""", 1, [
        question(1, r"""A **function** gives exactly **one** output for each input. If any input is paired with two different outputs, it is not a function. The **range** is the set of outputs actually produced.""", [
            part("(a)", 0, r"""Each set below is a set of (input, output) pairs. Which one is **not** a function?

**(A)** $\lbrace (1, 2),\ (2, 3),\ (3, 4) \rbrace$

**(B)** $\lbrace (1, 2),\ (1, 3),\ (2, 4) \rbrace$

**(C)** $\lbrace (1, 5),\ (2, 5),\ (3, 5) \rbrace$

**(D)** $\lbrace (0, 1),\ (1, 0) \rbrace$

Type the letter of your answer.""",
                 "B", "multi", LETTER, 5,
                 r"""In (B) the input $1$ is paired with **two** outputs, $2$ and $3$. A function must give exactly one output for each input, so (B) is not a function.

(C) is still a function: different inputs may share an output.

**Answer:** B"""),
            part("(b)", 1, r"""The function $f(x) = x^2 - 1$ has domain $\lbrace -2, -1, 0, 1, 2 \rbrace$. What is its **range**?

**(A)** $\lbrace -2, -1, 0, 1, 2 \rbrace$

**(B)** $\lbrace 3, 0, -1, 0, 3 \rbrace$

**(C)** $\lbrace -1, 0, 3 \rbrace$

**(D)** $\lbrace -1, 3 \rbrace$

Type the letter of your answer.""",
                 "C", "multi", LETTER, 5,
                 r"""Work out each output:

$$f(-2) = 3,\quad f(-1) = 0,\quad f(0) = -1,\quad f(1) = 0,\quad f(2) = 3$$

Each output is listed **once** in a set, so (B) is not the range, and (D) misses $0$. (A) is the domain.

**Answer:** C, $\lbrace -1, 0, 3 \rbrace$"""),
        ]),
        question(2, r"""Replace every $x$ in the rule with the input, in brackets. To find the input that gives a particular output, set $f(x)$ equal to that output and solve.""", [
            part("(a)", 0, r"""$f(x) = 3x - 5$. Find $f(4)$.""",
                 "7", "numeric", NUM, 5,
                 r"""$$f(4) = 3(4) - 5 = 12 - 5 = 7$$

**Answer:** $7$"""),
            part("(b)", 1, r"""Find the value of $x$ for which $f(x) = 10$.""",
                 "5", "numeric", NUM, 5,
                 r"""$$3x - 5 = 10 \;\Rightarrow\; 3x = 15 \;\Rightarrow\; x = 5$$

**Answer:** $x = 5$"""),
            part("(c)", 2, r"""Find $f(2a)$ in terms of $a$.""",
                 "6*a - 5", "expression", "An expression in $a$ (e.g., 4a + 1)", 5,
                 r"""Replace $x$ with $2a$:

$$f(2a) = 3(2a) - 5 = 6a - 5$$

**Answer:** $6a - 5$"""),
        ]),
        question(3, r"""$f(g(x))$ means: apply $g$ **first**, then put the result into $f$. Work from the inside out.""", [
            part("(a)", 0, r"""$f(x) = 2x + 1$ and $g(x) = x^2$. Find $f(g(3))$.""",
                 "19", "numeric", NUM, 5,
                 r"""Inside first: $g(3) = 3^2 = 9$.

Then $f(9) = 2(9) + 1 = 19$.

**Answer:** $19$"""),
            part("(b)", 1, r"""Find $g(f(3))$.""",
                 "49", "numeric", NUM, 5,
                 r"""Inside first: $f(3) = 2(3) + 1 = 7$.

Then $g(7) = 7^2 = 49$.

Notice $f(g(3)) \neq g(f(3))$: the order matters.

**Answer:** $49$"""),
            part("(c)", 2, r"""Write $f(g(x))$ as an expression in $x$.""",
                 "2*x**2 + 1", "expression", EXPR, 5,
                 r"""Put $g(x) = x^2$ into $f$ in place of $x$:

$$f(g(x)) = f(x^2) = 2x^2 + 1$$

**Answer:** $2x^2 + 1$"""),
        ]),
        question(4, r"""The sign of the leading coefficient decides the shape. Quadratic: positive gives $\cup$, negative gives $\cap$. Cubic: positive starts low and ends high; negative starts high and ends low. An exponential $a^x$ always passes through $(0, 1)$.""", [
            part("(a)", 0, r"""Which of these functions has a $\cap$-shaped graph?

**(A)** $f(x) = x^2 - 4$

**(B)** $f(x) = -x^2 + 1$

**(C)** $f(x) = 2x + 1$

**(D)** $f(x) = 2^x$

Type the letter of your answer.""",
                 "B", "multi", LETTER, 5,
                 r"""A quadratic is $\cap$-shaped when the coefficient of $x^2$ is **negative**. Only (B), with $-x^2$, qualifies. (A) is $\cup$-shaped, (C) is a straight line and (D) is an exponential curve.

**Answer:** B"""),
            part("(b)", 1, r"""Describe the graph of $f(x) = -x^3 + 2x^2 + 5$ from left to right.

**(A)** It starts low and ends high.

**(B)** It starts high and ends low.

**(C)** It starts high and ends high.

**(D)** It starts low and ends low.

Type the letter of your answer.""",
                 "B", "multi", LETTER, 5,
                 r"""The coefficient of $x^3$ is $-1$, which is negative. A cubic with a negative leading coefficient starts **high** on the left and ends **low** on the right.

**Answer:** B"""),
            part("(c)", 2, r"""At what value of $y$ does the graph of $f(x) = 5^x$ cross the $y$-axis?""",
                 "1", "numeric", NUM, 5,
                 r"""The graph crosses the $y$-axis where $x = 0$:

$$f(0) = 5^0 = 1$$

Every exponential $a^x$ passes through $(0, 1)$.

**Answer:** $1$"""),
        ]),
        question(5, r"""To complete the square on $x^2 + bx + c$, halve $b$ to get $p$, then $x^2 + bx + c = (x + p)^2 - p^2 + c$. The turning point of $(x + p)^2 + q$ is $(-p, q)$.""", [
            part("(a)", 0, r"""$f(x) = x^2 - 4x + 7$ can be written as $(x + p)^2 + q$.

Find the value of $p$.""",
                 "-2", "numeric", NUM, 5,
                 r"""Half of the $x$ coefficient $-4$ is $-2$, so $p = -2$:

$$x^2 - 4x + 7 = (x - 2)^2 - 4 + 7 = (x - 2)^2 + 3$$

**Answer:** $p = -2$"""),
            part("(b)", 1, r"""Find the value of $q$.""",
                 "3", "numeric", NUM, 5,
                 r"""From (a): $(x - 2)^2 - 4 + 7 = (x - 2)^2 + 3$.

**Answer:** $q = 3$"""),
            part("(c)", 2, r"""Hence write down the coordinates of the turning point of the graph of $f$.""",
                 "2, 3", "numeric", POINT, 5,
                 r"""$(x - 2)^2 \geq 0$, so $f(x)$ is smallest when $x - 2 = 0$, i.e. $x = 2$. Then $f(2) = 3$.

**Answer:** $(2,\ 3)$, a minimum point"""),
        ]),
        question(6, r"""$y = f(x) + k$ moves the graph **up** $k$. $y = f(x - h)$ moves it **right** $h$, and $y = f(x + h)$ moves it **left** $h$: the sign inside the bracket works the opposite way to what you might expect.""", [
            part("(a)", 0, r"""The graph of $g(x) = x^2 - 4$ is moved to give $y = (x + 3)^2 - 4$. Describe the move.

**(A)** 3 units right

**(B)** 3 units left

**(C)** 3 units up

**(D)** 3 units down

Type the letter of your answer.""",
                 "B", "multi", LETTER, 5,
                 r"""$(x + 3)^2 - 4 = g(x + 3)$. Replacing $x$ by $x + 3$ moves the graph **3 units to the left**. Check: the turning point moves from $(0, -4)$ to $(-3, -4)$.

**Answer:** B"""),
            part("(b)", 1, r"""The graph of $y = g(x) + 3$ crosses the $y$-axis at $(0, c)$. Find $c$.""",
                 "-1", "numeric", NUM, 5,
                 r"""$g(x) + 3 = x^2 - 4 + 3 = x^2 - 1$. At $x = 0$, $y = -1$.

**Answer:** $c = -1$"""),
            part("(c)", 2, r"""Write down the coordinates of the turning point of $y = g(x - 2)$.""",
                 "2, -4", "numeric", POINT, 5,
                 r"""$g(x - 2) = (x - 2)^2 - 4$. The graph of $g$ moves **2 units right**, so its turning point moves from $(0, -4)$ to $(2, -4)$.

**Answer:** $(2,\ -4)$"""),
        ]),
        question(7, r"""To find an inverse: write $y = f(x)$, rearrange to make $x$ the subject, then swap $x$ and $y$. The inverse undoes $f$, so $f^{-1}(f(a)) = a$.""", [
            part("(a)", 0, r"""$f(x) = 2x + 3$. Find $f^{-1}(x)$.""",
                 "(x - 3)/2", "expression", EXPR, 10,
                 r"""Let $y = 2x + 3$. Make $x$ the subject:

$$y - 3 = 2x \;\Rightarrow\; x = \frac{y - 3}{2}$$

Swap $x$ and $y$:

$$f^{-1}(x) = \frac{x - 3}{2}$$

**Answer:** $f^{-1}(x) = \dfrac{x - 3}{2}$"""),
            part("(b)", 1, r"""Find $f^{-1}(11)$.""",
                 "4", "numeric", NUM, 5,
                 r"""$$f^{-1}(11) = \frac{11 - 3}{2} = 4$$

Check: $f(4) = 2(4) + 3 = 11$. ✓

**Answer:** $4$"""),
        ]),
    ]),

    ("""Workout""", 2, [
        question(1, r"""Build $f(g(x))$ by putting the whole of $g(x)$, in brackets, wherever $x$ appears in $f$. Then expand and simplify before solving.""", [
            part("(a)", 0, r"""$f(x) = x^2 - 3$ and $g(x) = 2x + 1$. Find $f(g(x))$, simplified.""",
                 "4*x**2 + 4*x - 2", "expression", EXPR, 10,
                 r"""$$f(g(x)) = (2x + 1)^2 - 3 = 4x^2 + 4x + 1 - 3 = 4x^2 + 4x - 2$$

**Answer:** $4x^2 + 4x - 2$"""),
            part("(b)", 1, r"""Solve $f(g(x)) = 6$.""",
                 "-2, 1", "numeric", NUMS, 10,
                 r"""$$4x^2 + 4x - 2 = 6 \;\Rightarrow\; 4x^2 + 4x - 8 = 0 \;\Rightarrow\; x^2 + x - 2 = 0$$

$$(x + 2)(x - 1) = 0 \;\Rightarrow\; x = -2 \text{ or } x = 1$$

**Answer:** $x = -2,\ 1$"""),
        ]),
        question(2, r"""Take out the coefficient of $x^2$ first: $2x^2 - 12x + 10 = 2(x^2 - 6x) + 10$. Then complete the square inside the bracket. The turning point of $a(x + p)^2 + q$ is $(-p, q)$.""", [
            part("(a)", 0, r"""$f(x) = 2x^2 - 12x + 10$ can be written as $a(x + p)^2 + q$.

Find the value of $q$.""",
                 "-8", "numeric", NUM, 10,
                 r"""$$2x^2 - 12x + 10 = 2(x^2 - 6x) + 10 = 2\bigl[(x - 3)^2 - 9\bigr] + 10 = 2(x - 3)^2 - 8$$

So $a = 2$, $p = -3$, $q = -8$.

**Answer:** $q = -8$"""),
            part("(b)", 1, r"""Write down the coordinates of the turning point.""",
                 "3, -8", "numeric", POINT, 5,
                 r"""$f(x) = 2(x - 3)^2 - 8$, with turning point at $x = 3$, $f(3) = -8$. Since $a = 2 > 0$ it is a minimum.

**Answer:** $(3,\ -8)$"""),
            part("(c)", 2, r"""Use the completed square form to find the roots of $f(x) = 0$.""",
                 "1, 5", "numeric", NUMS, 10,
                 r"""$$2(x - 3)^2 - 8 = 0 \;\Rightarrow\; (x - 3)^2 = 4 \;\Rightarrow\; x - 3 = \pm 2$$

$$x = 1 \text{ or } x = 5$$

**Answer:** $x = 1,\ 5$"""),
        ]),
        question(3, r"""$f(x) = g(x)$ where the two graphs **meet**. $f(x) < g(x)$ where the graph of $f$ is **below** the graph of $g$: between the meeting points, if $f$ is a $\cup$-shaped quadratic and $g$ a line.""", [
            part("(a)", 0, r"""$f(x) = x^2 - 2x - 3$ and $g(x) = x + 1$. Find the $x$ values where the graphs of $f$ and $g$ meet.""",
                 "-1, 4", "numeric", NUMS, 10,
                 r"""$$x^2 - 2x - 3 = x + 1 \;\Rightarrow\; x^2 - 3x - 4 = 0 \;\Rightarrow\; (x - 4)(x + 1) = 0$$

**Answer:** $x = -1,\ 4$"""),
            part("(b)", 1, r"""For which values of $x$ is $f(x) < g(x)$?

**(A)** $x < -1$ or $x > 4$

**(B)** $-1 < x < 4$

**(C)** $-4 < x < 1$

**(D)** $x > 4$

Type the letter of your answer.""",
                 "B", "multi", LETTER, 5,
                 r"""$f(x) - g(x) = (x - 4)(x + 1)$, a $\cup$-shaped curve that is negative **between** its roots. So the parabola is below the line for $-1 < x < 4$. Check $x = 0$: $f(0) = -3 < g(0) = 1$. ✓

**Answer:** B"""),
        ]),
        question(4, r"""The solutions of $f(x) = k$ are where the horizontal line $y = k$ meets the graph. For a $\cup$-shaped quadratic, a line through the minimum point touches it once; a line above it cuts twice; a line below misses.""", [
            part("(a)", 0, r"""$f(x) = x^2 - 4x$. For what value of $k$ does $f(x) = k$ have exactly **one** solution?""",
                 "-4", "numeric", NUM, 10,
                 r"""$f(x) = (x - 2)^2 - 4$, so the minimum point is $(2, -4)$. The line $y = -4$ touches the graph only there.

**Answer:** $k = -4$"""),
            part("(b)", 1, r"""How many solutions does $f(x) = 5$ have?""",
                 "2", "numeric", NUM, 5,
                 r"""$5$ is above the minimum value $-4$, so the line $y = 5$ cuts the $\cup$-shaped graph twice. Check: $x^2 - 4x - 5 = 0 \Rightarrow (x - 5)(x + 1) = 0$, two solutions.

**Answer:** $2$"""),
        ]),
        question(5, r"""**Injective:** different inputs always give different outputs (no horizontal line meets the graph twice). **Surjective:** every element of the codomain is an output. **Bijective:** both.""", [
            part("(a)", 0, r"""$f : \mathbb{R} \to \mathbb{R}$, $f(x) = x^2$. Which describes $f$?

**(A)** Injective and surjective

**(B)** Injective but not surjective

**(C)** Surjective but not injective

**(D)** Neither injective nor surjective

Type the letter of your answer.""",
                 "D", "multi", LETTER, 5,
                 r"""Not injective: $f(-2) = f(2) = 4$.

Not surjective: no real $x$ gives $x^2 = -1$, so negative numbers in the codomain $\mathbb{R}$ are never reached.

**Answer:** D"""),
            part("(b)", 1, r"""$g : \mathbb{R} \to \mathbb{R}$, $g(x) = 3x - 2$. Which describes $g$?

**(A)** Injective and surjective

**(B)** Injective but not surjective

**(C)** Surjective but not injective

**(D)** Neither injective nor surjective

Type the letter of your answer.""",
                 "A", "multi", LETTER, 5,
                 r"""Injective: if $3a - 2 = 3b - 2$ then $a = b$.

Surjective: any $y$ is reached by $x = \frac{y + 2}{3}$.

So $g$ is bijective.

**Answer:** A"""),
            part("(c)", 2, r"""$h : \mathbb{N} \to \mathbb{N}$, $h(x) = 2x$. Which describes $h$?

**(A)** Injective and surjective

**(B)** Injective but not surjective

**(C)** Surjective but not injective

**(D)** Neither injective nor surjective

Type the letter of your answer.""",
                 "B", "multi", LETTER, 5,
                 r"""Injective: different natural numbers have different doubles.

Not surjective: the outputs are only the even numbers, so an odd number such as $3$ in the codomain is never reached.

**Answer:** B"""),
        ]),
        question(6, r"""Write $y = \dfrac{2x + 1}{x - 3}$, multiply both sides by $(x - 3)$, gather the $x$ terms on one side and factor $x$ out. Then swap $x$ and $y$.""", [
            part("(a)", 0, r"""$f(x) = \dfrac{2x + 1}{x - 3}$, $x \neq 3$. Find $f^{-1}(x)$.""",
                 "(3*x + 1)/(x - 2)", "expression", EXPR, 15,
                 r"""Let $y = \dfrac{2x + 1}{x - 3}$:

$$y(x - 3) = 2x + 1 \;\Rightarrow\; xy - 3y = 2x + 1 \;\Rightarrow\; xy - 2x = 3y + 1$$

$$x(y - 2) = 3y + 1 \;\Rightarrow\; x = \frac{3y + 1}{y - 2}$$

Swap $x$ and $y$:

**Answer:** $f^{-1}(x) = \dfrac{3x + 1}{x - 2}$"""),
            part("(b)", 1, r"""Find $f^{-1}(5)$.""",
                 "16/3", "numeric", "A number or fraction (e.g., 7/2)", 5,
                 r"""$$f^{-1}(5) = \frac{3(5) + 1}{5 - 2} = \frac{16}{3}$$

Check: $f\left(\tfrac{16}{3}\right) = \dfrac{\tfrac{32}{3} + 1}{\tfrac{16}{3} - 3} = \dfrac{35/3}{7/3} = 5$. ✓

**Answer:** $\dfrac{16}{3}$"""),
        ]),
        question(7, r"""$\log_2 x$ and $2^x$ undo each other: $\log_2(2^a) = a$. To solve $3 \cdot 2^x = 96$, divide first, then write the result as a power of $2$. Every graph $y = \log_a x$ crosses the $x$-axis at $(1, 0)$.""", [
            part("(a)", 0, r"""$f(x) = 2^x$ and $g(x) = \log_2 x$. Find $g(f(5))$.""",
                 "5", "numeric", NUM, 5,
                 r"""$f(5) = 2^5 = 32$, then $g(32) = \log_2 32 = 5$, since $2^5 = 32$.

**Answer:** $5$"""),
            part("(b)", 1, r"""Solve $3 \cdot 2^x = 96$.""",
                 "5", "numeric", NUM, 10,
                 r"""$$2^x = \frac{96}{3} = 32 = 2^5 \;\Rightarrow\; x = 5$$

**Answer:** $x = 5$"""),
            part("(c)", 2, r"""At what value of $x$ does the graph of $y = \log_2 x$ cross the $x$-axis?""",
                 "1", "numeric", NUM, 5,
                 r"""It crosses where $y = 0$: $\log_2 x = 0 \Rightarrow x = 2^0 = 1$.

**Answer:** $x = 1$"""),
        ]),
    ]),

    ("""Stretch""", 3, [
        question(1, r"""A quadratic is not injective on all of $\mathbb{R}$, because it rises on both sides of its turning point. Restrict the domain to one side of the turning point and it has an inverse. Complete the square first to find that point.""", [
            part("(a)", 0, r"""$f(x) = x^2 - 6x + 5$, for $x \geq a$. Find the **smallest** value of $a$ for which $f$ is injective.""",
                 "3", "numeric", NUM, 10,
                 r"""$f(x) = (x - 3)^2 - 4$, with its turning point at $x = 3$. To the right of $x = 3$ the graph only rises, so $f$ is injective for $x \geq 3$, and not for any $a < 3$.

**Answer:** $a = 3$"""),
            part("(b)", 1, r"""With this domain, find $f^{-1}(x)$.""",
                 "3 + sqrt(x + 4)", "expression", EXPR, 15,
                 r"""Let $y = (x - 3)^2 - 4$:

$$y + 4 = (x - 3)^2 \;\Rightarrow\; x - 3 = \pm\sqrt{y + 4}$$

Since $x \geq 3$, take the positive root: $x = 3 + \sqrt{y + 4}$. Swap $x$ and $y$:

**Answer:** $f^{-1}(x) = 3 + \sqrt{x + 4}$"""),
            part("(c)", 2, r"""Find $f^{-1}(12)$.""",
                 "7", "numeric", NUM, 5,
                 r"""$$f^{-1}(12) = 3 + \sqrt{16} = 7$$

Check: $f(7) = 49 - 42 + 5 = 12$. ✓

**Answer:** $7$"""),
        ]),
        question(2, r"""Write each composite as an expression in $x$ first, then set them equal (or set one equal to the other function) and solve.""", [
            part("(a)", 0, r"""$f(x) = x + 2$ and $g(x) = x^2$. Solve $g(f(x)) = f(x)$.""",
                 "-2, -1", "numeric", NUMS, 10,
                 r"""$g(f(x)) = (x + 2)^2$. So

$$(x + 2)^2 = x + 2 \;\Rightarrow\; (x + 2)(x + 2 - 1) = 0 \;\Rightarrow\; (x + 2)(x + 1) = 0$$

Don't divide by $(x + 2)$: that loses the root $x = -2$.

**Answer:** $x = -2,\ -1$"""),
            part("(b)", 1, r"""Solve $g(f(x)) = f(g(x))$.""",
                 "-0.5", "numeric", "Number or fraction (e.g., -3/4)", 10,
                 r"""$g(f(x)) = (x + 2)^2 = x^2 + 4x + 4$ and $f(g(x)) = x^2 + 2$.

$$x^2 + 4x + 4 = x^2 + 2 \;\Rightarrow\; 4x = -2 \;\Rightarrow\; x = -\tfrac{1}{2}$$

**Answer:** $x = -\tfrac{1}{2}$"""),
        ]),
        question(3, r"""Group the cubic in pairs: $x^2(x + 1) - 4(x + 1)$. For $f(x) = -4$, move everything to one side first; $x$ will be a common factor.""", [
            part("(a)", 0, r"""$f(x) = x^3 + x^2 - 4x - 4$ factorises as $(x + 1)(x - b)(x + b)$, where $b > 0$. Find $b$.""",
                 "2", "numeric", NUM, 10,
                 r"""$$x^3 + x^2 - 4x - 4 = x^2(x + 1) - 4(x + 1) = (x + 1)(x^2 - 4) = (x + 1)(x - 2)(x + 2)$$

So $b = 2$, and the roots of $f(x) = 0$ are $x = -2,\ -1,\ 2$.

**Answer:** $b = 2$"""),
            part("(b)", 1, r"""One solution of $f(x) = -4$ is $x = 0$. Find the other two, correct to two decimal places.""",
                 "-2.56, 1.56", "numeric", "Two numbers to 2 decimal places, separated by a comma, smallest first (e.g., -1.25, 3.40)", 15,
                 r"""$$x^3 + x^2 - 4x - 4 = -4 \;\Rightarrow\; x^3 + x^2 - 4x = 0 \;\Rightarrow\; x(x^2 + x - 4) = 0$$

So $x = 0$, or

$$x = \frac{-1 \pm \sqrt{1 + 16}}{2} = \frac{-1 \pm \sqrt{17}}{2}$$

$\sqrt{17} \approx 4.1231$, giving $x \approx 1.56$ or $x \approx -2.56$.

**Answer:** $x = -2.56,\ 1.56$ (and $x = 0$)"""),
            part("(c)", 2, r"""Sketch the graph of $f$ for $-3 \leq x \leq 3$, showing where it crosses both axes.""",
                 "Crosses the x-axis at -2, -1 and 2 and the y-axis at -4; starts low at (-3, -10), ends high at (3, 20)",
                 "manual",
                 "A sketch on paper. Use Photograph my working to get feedback on it.", 10,
                 r"""Plot the intercepts and the end points:

- $x$-axis: $(-2, 0)$, $(-1, 0)$, $(2, 0)$
- $y$-axis: $f(0) = -4$, so $(0, -4)$
- Ends: $f(-3) = -10$ and $f(3) = 20$

The coefficient of $x^3$ is positive, so the curve starts low and ends high. It rises through $(-2, 0)$ to a local maximum between $-2$ and $-1$, falls through $(-1, 0)$ and $(0, -4)$ to a local minimum between $0$ and $2$, then rises through $(2, 0)$."""),
        ]),
        question(4, r"""A graph $y = a(x + p)^2 + q$ with turning point $(h, k)$ is $y = a(x - h)^2 + k$. Substitute the other point to find $a$.""", [
            part("(a)", 0, r"""A parabola $y = a(x + p)^2 + q$ has its turning point at $(-1, 5)$ and passes through $(1, -3)$. Find the value of $a$.""",
                 "-2", "numeric", NUM, 10,
                 r"""Turning point $(-1, 5)$ gives $y = a(x + 1)^2 + 5$.

Through $(1, -3)$:

$$-3 = a(2)^2 + 5 \;\Rightarrow\; 4a = -8 \;\Rightarrow\; a = -2$$

**Answer:** $a = -2$"""),
            part("(b)", 1, r"""Where does this parabola cross the $y$-axis? Give the $y$ value.""",
                 "3", "numeric", NUM, 5,
                 r"""$$y = -2(0 + 1)^2 + 5 = 3$$

**Answer:** $y = 3$"""),
        ]),
        question(5, r"""For surjectivity the codomain must be exactly the set of outputs, so complete the square to find the least output. For injectivity, look for two different inputs with the same output.""", [
            part("(a)", 0, r"""$f : \mathbb{R} \to [k, \infty)$, $f(x) = x^2 + 6x + 11$. Find the value of $k$ that makes $f$ surjective.""",
                 "2", "numeric", NUM, 10,
                 r"""$f(x) = (x + 3)^2 + 2$. The least output is $2$ (at $x = -3$) and every value above it is reached, so the range is $[2, \infty)$. The codomain must equal the range.

**Answer:** $k = 2$"""),
            part("(b)", 1, r"""Is $f$ injective?

**(A)** Yes, because it is a quadratic

**(B)** Yes, because its range is $[k, \infty)$

**(C)** No, because $f(-4) = f(-2)$

**(D)** No, because $f(0)$ is not in the codomain

Type the letter of your answer.""",
                 "C", "multi", LETTER, 5,
                 r"""$f(-4) = 16 - 24 + 11 = 3$ and $f(-2) = 4 - 12 + 11 = 3$. Two different inputs give the same output, so $f$ is not injective. (D) is false: $f(0) = 11 \geq 2$.

**Answer:** C"""),
        ]),
        question(6, r"""The graph of $f^{-1}$ is the reflection of the graph of $f$ in the line $y = x$, so the point $(a, b)$ on $f$ becomes $(b, a)$ on $f^{-1}$. And $f^{-1}(b)$ is the input that $f$ sends to $b$.""", [
            part("(a)", 0, r"""The point $(2, 7)$ is on the graph of a bijective function $f$. Write down the point it becomes on the graph of $f^{-1}$.""",
                 "7, 2", "numeric", POINT, 5,
                 r"""Reflecting in $y = x$ swaps the coordinates.

**Answer:** $(7,\ 2)$"""),
            part("(b)", 1, r"""$f(x) = x^3 + 1$. Find $f^{-1}(28)$.""",
                 "3", "numeric", NUM, 10,
                 r"""$f^{-1}(28)$ is the $x$ with $f(x) = 28$:

$$x^3 + 1 = 28 \;\Rightarrow\; x^3 = 27 \;\Rightarrow\; x = 3$$

**Answer:** $3$"""),
        ]),
    ]),
]


class Command(BaseCommand):
    help = "Add or update the Functions practice questions"

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

                    question_row, made = Question.objects.update_or_create(
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
                        f'    {"created" if made else "updated"} question {question_row.order}'
                    )

                    for p in entry["parts"]:
                        QuestionPart.objects.update_or_create(
                            question=question_row,
                            label=p["label"],
                            defaults={
                                "prompt": p["prompt"],
                                "answer": p["answer"],
                                "expected_format": p["expected_format"],
                                "solution": p["solution"],
                                "expected_type": p["expected_type"],
                                "max_marks": p["max_marks"],
                                "order": p["order"],
                                "solution_unlock_after_attempts": p["unlock"],
                                "scale": p["scale"],
                                "is_quickkick_suitable": p["qk"],
                            },
                        )
                        parts += 1

            if dry_run:
                transaction.set_rollback(True)

        prefix = "Would touch" if dry_run else "Wrote"
        self.stdout.write(self.style.SUCCESS(
            f"\n{prefix} {questions} questions and {parts} parts."
        ))
