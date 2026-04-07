"""
Management command to add Algebra-Inequalities and Factorisation topic
with Cubic Factorisation and Discriminants sections.
"""
from django.core.management.base import BaseCommand
from core.models import Subject
from interactive_lessons.models import Topic, Section, Question, QuestionPart


class Command(BaseCommand):
    help = "Add Algebra-Inequalities and Factorisation topic with 6 questions"

    def handle(self, *args, **options):
        maths = Subject.objects.get(slug='maths')

        topic, created = Topic.objects.get_or_create(
            name='Algebra-Inequalities and Factorisation',
            defaults={'subject': maths}
        )
        if not created:
            topic.subject = maths
            topic.save()
        self.stdout.write(f"Topic: {topic.name} (id={topic.id}, created={created})")

        sec_cubic, _ = Section.objects.get_or_create(
            name='Cubic Factorisation',
            topic=topic,
            defaults={'order': 1}
        )
        sec_disc, _ = Section.objects.get_or_create(
            name='Discriminants',
            topic=topic,
            defaults={'order': 2}
        )

        # Skip if questions already exist
        if Question.objects.filter(topic=topic).exists():
            self.stdout.write(self.style.WARNING("Questions already exist for this topic. Skipping."))
            return

        # --- Q1: f(x) = 3x^3 - 10x^2 + 9x - 2, root x=2 ---
        q1 = Question.objects.create(
            topic=topic, order=1, section=sec_cubic,
            hint="If $x = a$ is a root of $f(x)$, then $(x - a)$ is a factor. Use the Factor Theorem and then divide the cubic by the linear factor to get a quadratic, which you can factorise further.",
            is_exam_question=False, is_copyrighted=True,
        )
        QuestionPart.objects.create(
            question=q1, label="(a)", order=0,
            prompt="Given that $x = 2$ is a root of the cubic function\n\n$$f(x) = 3x^3 - 10x^2 + 9x - 2$$\n\nWrite down a factor of $f(x)$.",
            answer="(x-2)",
            expected_format="Linear factor (e.g., $(x-5)$ or $(x+3)$)",
            expected_type="expression", max_marks=5,
            solution="**Step 1:** Apply the Factor Theorem.\n\nIf $x = 2$ is a root of $f(x)$, then $f(2) = 0$.\n\n**Step 2:** Therefore $(x - 2)$ is a factor of $f(x)$.\n\n**Answer:** $(x - 2)$",
        )
        QuestionPart.objects.create(
            question=q1, label="(b)", order=1,
            prompt="Divide $f(x)$ by this factor to find the quadratic factor.",
            answer="3x^2-4x+1",
            expected_format="Quadratic expression (e.g., $2x^2+5x-3$ or $x^2-7x+12$)",
            expected_type="expression", max_marks=10,
            solution="**Step 1:** Perform polynomial long division of $3x^3 - 10x^2 + 9x - 2$ by $(x - 2)$.\n\n**Step 2:** Divide $3x^3$ by $x$: gives $3x^2$.\nMultiply: $3x^2(x - 2) = 3x^3 - 6x^2$.\nSubtract: $-10x^2 - (-6x^2) = -4x^2$. Bring down $+9x$.\n\n**Step 3:** Divide $-4x^2$ by $x$: gives $-4x$.\nMultiply: $-4x(x - 2) = -4x^2 + 8x$.\nSubtract: $9x - 8x = x$. Bring down $-2$.\n\n**Step 4:** Divide $x$ by $x$: gives $+1$.\nMultiply: $1(x - 2) = x - 2$.\nSubtract: $-2 - (-2) = 0$.\n\n**Answer:** $3x^2 - 4x + 1$",
        )
        QuestionPart.objects.create(
            question=q1, label="(c)", order=2,
            prompt="Hence, or otherwise, write $f(x)$ in fully factorised form and state all roots of $f(x)$.",
            answer="(x-2)(3x-1)(x-1)",
            expected_format="Factorised form (e.g., $(x-5)(2x+3)(x-1)$)",
            expected_type="expression", max_marks=10,
            solution="**Step 1:** Factorise the quadratic $3x^2 - 4x + 1$.\n\nFind two numbers that multiply to $3 \\times 1 = 3$ and add to $-4$: these are $-3$ and $-1$.\n\n$3x^2 - 3x - x + 1 = 3x(x - 1) - 1(x - 1) = (3x - 1)(x - 1)$\n\n**Step 2:** Write in fully factorised form:\n\n$$f(x) = (x - 2)(3x - 1)(x - 1)$$\n\n**Step 3:** The roots are: $x = 2$, $x = \\frac{1}{3}$, $x = 1$.\n\n**Answer:** $f(x) = (x - 2)(3x - 1)(x - 1)$; roots: $x = 2, \\frac{1}{3}, 1$",
        )
        self.stdout.write(f"Created Q1 (id={q1.id})")

        # --- Q2: g(x) = x^3 - 2x^2 - 5x + 6, factor (x-3) ---
        q2 = Question.objects.create(
            topic=topic, order=2, section=sec_cubic,
            hint="When given a factor $(x - a)$, divide the cubic by it using algebraic long division or synthetic division to find the remaining quadratic factor. Then factorise the quadratic.",
            is_exam_question=False, is_copyrighted=True,
        )
        QuestionPart.objects.create(
            question=q2, label="(a)", order=0,
            prompt="$(x - 3)$ is a factor of\n\n$$g(x) = x^3 - 2x^2 - 5x + 6$$\n\nUsing algebraic long division, or otherwise, find the values of $a$ and $b$ such that\n\n$$g(x) = (x - 3)(x^2 + ax + b)$$",
            answer="a=1,b=-2",
            expected_format="Two values (e.g., a=3,b=5 or a=-1,b=7)",
            expected_type="exact", max_marks=10,
            solution="**Step 1:** Perform polynomial long division of $x^3 - 2x^2 - 5x + 6$ by $(x - 3)$.\n\n**Step 2:** $x^3 \\div x = x^2$. Multiply: $x^2(x-3) = x^3 - 3x^2$. Subtract: $-2x^2 + 3x^2 = x^2$. Bring down $-5x$.\n\n**Step 3:** $x^2 \\div x = x$. Multiply: $x(x-3) = x^2 - 3x$. Subtract: $-5x + 3x = -2x$. Bring down $+6$.\n\n**Step 4:** $-2x \\div x = -2$. Multiply: $-2(x-3) = -2x + 6$. Subtract: $6 - 6 = 0$.\n\n**Step 5:** So $g(x) = (x - 3)(x^2 + x - 2)$, giving $a = 1$ and $b = -2$.\n\n**Answer:** $a = 1$, $b = -2$",
        )
        QuestionPart.objects.create(
            question=q2, label="(b)", order=1,
            prompt="Hence factorise $g(x)$ completely.",
            answer="(x-3)(x+2)(x-1)",
            expected_format="Factorised form (e.g., $(x-5)(x+1)(x-4)$)",
            expected_type="expression", max_marks=5,
            solution="**Step 1:** Factorise $x^2 + x - 2$.\n\nFind two numbers that multiply to $-2$ and add to $1$: these are $2$ and $-1$.\n\n$x^2 + x - 2 = (x + 2)(x - 1)$\n\n**Step 2:** Therefore:\n\n$$g(x) = (x - 3)(x + 2)(x - 1)$$\n\n**Answer:** $(x - 3)(x + 2)(x - 1)$",
        )
        QuestionPart.objects.create(
            question=q2, label="(c)", order=2,
            prompt="Write down all roots of $g(x)$.",
            answer="3,-2,1",
            expected_format="Three values separated by commas (e.g., -4,2,5)",
            expected_type="exact", max_marks=5,
            solution="**Step 1:** Set each factor equal to zero:\n\n$x - 3 = 0 \\Rightarrow x = 3$\n$x + 2 = 0 \\Rightarrow x = -2$\n$x - 1 = 0 \\Rightarrow x = 1$\n\n**Answer:** $x = 3, -2, 1$",
        )
        self.stdout.write(f"Created Q2 (id={q2.id})")

        # --- Q3: h(x) = x^3 + 2x^2 - 11x - 12 ---
        q3 = Question.objects.create(
            topic=topic, order=3, section=sec_cubic,
            hint="To find a root by testing, try integer factors of the constant term (both positive and negative). If $f(a) = 0$, then $x = a$ is a root and $(x - a)$ is a factor.",
            is_exam_question=False, is_copyrighted=True,
        )
        QuestionPart.objects.create(
            question=q3, label="(a)", order=0,
            prompt="Let $h(x) = x^3 + 2x^2 - 11x - 12$.\n\nBy testing integer factors of the constant term, or otherwise, find one root of $h(x)$ and write down the corresponding linear factor.",
            answer="(x+1)",
            expected_format="Linear factor (e.g., $(x-5)$ or $(x+3)$)",
            expected_type="expression", max_marks=10,
            solution="**Step 1:** The constant term is $-12$. Its integer factors are: $\\pm 1, \\pm 2, \\pm 3, \\pm 4, \\pm 6, \\pm 12$.\n\n**Step 2:** Test $x = -1$:\n\n$h(-1) = (-1)^3 + 2(-1)^2 - 11(-1) - 12 = -1 + 2 + 11 - 12 = 0$\n\n**Step 3:** Since $h(-1) = 0$, $x = -1$ is a root and $(x + 1)$ is a factor.\n\n**Answer:** Root: $x = -1$, Factor: $(x + 1)$",
        )
        QuestionPart.objects.create(
            question=q3, label="(b)", order=1,
            prompt="Divide $h(x)$ by the factor found in part (a) to obtain a quadratic factor.",
            answer="x^2+x-12",
            expected_format="Quadratic expression (e.g., $x^2+3x-7$ or $x^2-5x+6$)",
            expected_type="expression", max_marks=10,
            solution="**Step 1:** Divide $x^3 + 2x^2 - 11x - 12$ by $(x + 1)$.\n\n**Step 2:** $x^3 \\div x = x^2$. Multiply: $x^2(x+1) = x^3 + x^2$. Subtract: $2x^2 - x^2 = x^2$. Bring down $-11x$.\n\n**Step 3:** $x^2 \\div x = x$. Multiply: $x(x+1) = x^2 + x$. Subtract: $-11x - x = -12x$. Bring down $-12$.\n\n**Step 4:** $-12x \\div x = -12$. Multiply: $-12(x+1) = -12x - 12$. Subtract: $-12 + 12 = 0$.\n\n**Answer:** $x^2 + x - 12$",
        )
        QuestionPart.objects.create(
            question=q3, label="(c)", order=2,
            prompt="Hence write $h(x)$ in fully factorised form and state all three roots.",
            answer="(x+1)(x+4)(x-3)",
            expected_format="Factorised form (e.g., $(x+2)(x-5)(x+1)$)",
            expected_type="expression", max_marks=5,
            solution="**Step 1:** Factorise $x^2 + x - 12$.\n\nFind two numbers that multiply to $-12$ and add to $1$: these are $4$ and $-3$.\n\n$x^2 + x - 12 = (x + 4)(x - 3)$\n\n**Step 2:** Fully factorised form:\n\n$$h(x) = (x + 1)(x + 4)(x - 3)$$\n\n**Step 3:** Roots: $x = -1, x = -4, x = 3$.\n\n**Answer:** $h(x) = (x + 1)(x + 4)(x - 3)$; roots: $x = -1, -4, 3$",
        )
        self.stdout.write(f"Created Q3 (id={q3.id})")

        # --- Q4: x^2 - 7x + m = 0 ---
        q4 = Question.objects.create(
            topic=topic, order=1, section=sec_disc,
            hint="The discriminant of $ax^2 + bx + c = 0$ is $\\Delta = b^2 - 4ac$. If $\\Delta > 0$: two distinct real roots. If $\\Delta = 0$: one repeated root. If $\\Delta < 0$: no real roots.",
            is_exam_question=False, is_copyrighted=True,
        )
        QuestionPart.objects.create(
            question=q4, label="(a)", order=0,
            prompt="Consider the quadratic equation\n\n$$x^2 - 7x + m = 0, \\quad m \\in \\mathbb{R}$$\n\nWrite down an expression for the discriminant $\\Delta$ of this equation in terms of $m$.",
            answer="49-4m",
            expected_format="Expression in terms of m (e.g., $25 - 4m$ or $m^2 - 16$)",
            expected_type="expression", max_marks=5,
            solution="**Step 1:** For $ax^2 + bx + c = 0$, the discriminant is $\\Delta = b^2 - 4ac$.\n\n**Step 2:** Here $a = 1$, $b = -7$, $c = m$.\n\n$\\Delta = (-7)^2 - 4(1)(m) = 49 - 4m$\n\n**Answer:** $\\Delta = 49 - 4m$",
        )
        QuestionPart.objects.create(
            question=q4, label="(b)", order=1,
            prompt="Find the value of $m$ for which the equation has exactly one real root (a repeated root).",
            answer="49/4",
            expected_format="Single value or fraction (e.g., 9 or 25/4)",
            expected_type="numeric", max_marks=5,
            solution="**Step 1:** For a repeated root, $\\Delta = 0$.\n\n$49 - 4m = 0$\n\n**Step 2:** Solve for $m$:\n\n$4m = 49$\n$m = \\frac{49}{4}$\n\n**Answer:** $m = \\frac{49}{4}$",
        )
        QuestionPart.objects.create(
            question=q4, label="(c)", order=2,
            prompt="Find the range of values of $m$ for which the equation has two distinct real roots.",
            answer="m<49/4",
            expected_format="Inequality (e.g., m<9 or m<25/4)",
            expected_type="exact", max_marks=5,
            solution="**Step 1:** For two distinct real roots, $\\Delta > 0$.\n\n$49 - 4m > 0$\n\n**Step 2:** Solve:\n\n$49 > 4m$\n$m < \\frac{49}{4}$\n\n**Answer:** $m < \\frac{49}{4}$",
        )
        QuestionPart.objects.create(
            question=q4, label="(d)", order=3,
            prompt="Find the range of values of $m$ for which the equation has no real roots.",
            answer="m>49/4",
            expected_format="Inequality (e.g., m>9 or m>25/4)",
            expected_type="exact", max_marks=5,
            solution="**Step 1:** For no real roots, $\\Delta < 0$.\n\n$49 - 4m < 0$\n\n**Step 2:** Solve:\n\n$49 < 4m$\n$m > \\frac{49}{4}$\n\n**Answer:** $m > \\frac{49}{4}$",
        )
        self.stdout.write(f"Created Q4 (id={q4.id})")

        # --- Q5: p(x) = x^3 - 7x^2 + 16x - 12, root x=3 ---
        q5 = Question.objects.create(
            topic=topic, order=2, section=sec_disc,
            hint="To show $x = a$ is a root, substitute into $p(x)$ and verify $p(a) = 0$. After dividing out the factor, use the discriminant $\\Delta = b^2 - 4ac$ to determine the nature of remaining roots.",
            is_exam_question=False, is_copyrighted=True,
        )
        QuestionPart.objects.create(
            question=q5, label="(a)", order=0,
            prompt="Let $p(x) = x^3 - 7x^2 + 16x - 12$.\n\nShow that $x = 3$ is a root of $p(x)$.",
            answer="0",
            expected_format="Show that $p(3) = 0$",
            expected_type="numeric", max_marks=5,
            solution="**Step 1:** Substitute $x = 3$ into $p(x)$:\n\n$p(3) = (3)^3 - 7(3)^2 + 16(3) - 12$\n\n**Step 2:** Evaluate:\n\n$= 27 - 63 + 48 - 12 = 0$\n\n**Step 3:** Since $p(3) = 0$, $x = 3$ is a root of $p(x)$.\n\n**Answer:** $p(3) = 0$, confirmed.",
        )
        QuestionPart.objects.create(
            question=q5, label="(b)", order=1,
            prompt="Divide $p(x)$ by $(x - 3)$ to obtain a quadratic factor $q(x)$.",
            answer="x^2-4x+4",
            expected_format="Quadratic expression (e.g., $x^2+3x-7$ or $x^2-5x+6$)",
            expected_type="expression", max_marks=10,
            solution="**Step 1:** Divide $x^3 - 7x^2 + 16x - 12$ by $(x - 3)$.\n\n**Step 2:** $x^3 \\div x = x^2$. Multiply: $x^2(x-3) = x^3 - 3x^2$. Subtract: $-7x^2 + 3x^2 = -4x^2$. Bring down $+16x$.\n\n**Step 3:** $-4x^2 \\div x = -4x$. Multiply: $-4x(x-3) = -4x^2 + 12x$. Subtract: $16x - 12x = 4x$. Bring down $-12$.\n\n**Step 4:** $4x \\div x = 4$. Multiply: $4(x-3) = 4x - 12$. Subtract: $-12 + 12 = 0$.\n\n**Answer:** $q(x) = x^2 - 4x + 4$",
        )
        QuestionPart.objects.create(
            question=q5, label="(c)", order=2,
            prompt="Find the discriminant of $q(x)$.",
            answer="0",
            expected_format="Single value (e.g., 12 or -8)",
            expected_type="numeric", max_marks=5,
            solution="**Step 1:** For $q(x) = x^2 - 4x + 4$, we have $a = 1$, $b = -4$, $c = 4$.\n\n**Step 2:** $\\Delta = b^2 - 4ac = (-4)^2 - 4(1)(4) = 16 - 16 = 0$\n\n**Answer:** $\\Delta = 0$",
        )
        QuestionPart.objects.create(
            question=q5, label="(d)", order=3,
            prompt="Hence determine the total number of real roots of $p(x)$, and justify your answer with reference to the discriminant.",
            answer="2",
            expected_format="Single integer (e.g., 1 or 3)",
            expected_type="numeric", max_marks=5,
            solution="**Step 1:** Since $\\Delta = 0$, the quadratic $q(x) = x^2 - 4x + 4$ has exactly one repeated root.\n\n**Step 2:** $q(x) = (x - 2)^2$, so $x = 2$ is a repeated root.\n\n**Step 3:** Combined with the root $x = 3$ from part (a), $p(x)$ has **2 distinct real roots**: $x = 3$ and $x = 2$ (with $x = 2$ being a repeated root).\n\n**Answer:** 2 distinct real roots ($x = 3$ and $x = 2$, where $x = 2$ is repeated)",
        )
        self.stdout.write(f"Created Q5 (id={q5.id})")

        # --- Q6: x^3 - 4x^2 + 2x + c = 0, factor (x-3), c=3 ---
        q6 = Question.objects.create(
            topic=topic, order=3, section=sec_disc,
            hint="Use the Factor Theorem: if $(x - a)$ is a factor of $f(x)$, then $f(a) = 0$. This lets you find unknown constants. Then divide and use the discriminant to analyse the remaining roots.",
            is_exam_question=False, is_copyrighted=True,
        )
        QuestionPart.objects.create(
            question=q6, label="(a)", order=0,
            prompt="The cubic equation\n\n$$x^3 - 4x^2 + 2x + c = 0, \\quad c \\in \\mathbb{R}$$\n\nhas $(x - 3)$ as a factor.\n\nUse the factor theorem to find the value of $c$.",
            answer="3",
            expected_format="Single value (e.g., 5 or -7)",
            expected_type="numeric", max_marks=5,
            solution="**Step 1:** If $(x - 3)$ is a factor, then $f(3) = 0$.\n\n**Step 2:** Substitute $x = 3$:\n\n$(3)^3 - 4(3)^2 + 2(3) + c = 0$\n$27 - 36 + 6 + c = 0$\n$-3 + c = 0$\n\n**Step 3:** $c = 3$\n\n**Answer:** $c = 3$",
        )
        QuestionPart.objects.create(
            question=q6, label="(b)", order=1,
            prompt="Using the value of $c$ found in part (a), divide the cubic by $(x - 3)$ to obtain a quadratic factor.",
            answer="x^2-x-1",
            expected_format="Quadratic expression (e.g., $x^2+3x-7$ or $x^2-5x+6$)",
            expected_type="expression", max_marks=10,
            solution="**Step 1:** With $c = 3$, the cubic is $x^3 - 4x^2 + 2x + 3$.\n\n**Step 2:** Divide by $(x - 3)$:\n\n$x^3 \\div x = x^2$. Multiply: $x^2(x-3) = x^3 - 3x^2$. Subtract: $-4x^2 + 3x^2 = -x^2$. Bring down $+2x$.\n\n**Step 3:** $-x^2 \\div x = -x$. Multiply: $-x(x-3) = -x^2 + 3x$. Subtract: $2x - 3x = -x$. Bring down $+3$.\n\n**Step 4:** $-x \\div x = -1$. Multiply: $-1(x-3) = -x + 3$. Subtract: $3 - 3 = 0$.\n\n**Answer:** $x^2 - x - 1$",
        )
        QuestionPart.objects.create(
            question=q6, label="(c)", order=2,
            prompt="Calculate the discriminant of this quadratic factor.",
            answer="5",
            expected_format="Single value (e.g., 12 or -8)",
            expected_type="numeric", max_marks=5,
            solution="**Step 1:** For $x^2 - x - 1$, we have $a = 1$, $b = -1$, $c = -1$.\n\n**Step 2:** $\\Delta = b^2 - 4ac = (-1)^2 - 4(1)(-1) = 1 + 4 = 5$\n\n**Answer:** $\\Delta = 5$",
        )
        QuestionPart.objects.create(
            question=q6, label="(d)", order=3,
            prompt="Describe fully the nature of the remaining roots of the cubic equation and justify your answer.",
            answer="Two distinct real irrational roots",
            expected_format="Description of root nature",
            expected_type="manual", max_marks=5,
            solution="**Step 1:** The discriminant $\\Delta = 5 > 0$.\n\n**Step 2:** Since $\\Delta > 0$, the quadratic $x^2 - x - 1 = 0$ has **two distinct real roots**.\n\n**Step 3:** Using the quadratic formula:\n\n$x = \\frac{1 \\pm \\sqrt{5}}{2}$\n\nSince $\\sqrt{5}$ is irrational, both roots are **irrational**.\n\n**Step 4:** The cubic has 3 real roots in total: $x = 3$, $x = \\frac{1 + \\sqrt{5}}{2}$, and $x = \\frac{1 - \\sqrt{5}}{2}$.\n\n**Answer:** The remaining two roots are distinct, real, and irrational: $x = \\frac{1 + \\sqrt{5}}{2}$ and $x = \\frac{1 - \\sqrt{5}}{2}$.",
        )
        self.stdout.write(f"Created Q6 (id={q6.id})")

        self.stdout.write(self.style.SUCCESS(
            f"\nDone! Created 6 questions (21 parts) in '{topic.name}'"
        ))
