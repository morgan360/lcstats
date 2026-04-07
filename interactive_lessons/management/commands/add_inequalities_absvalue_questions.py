"""
Management command to add Inequalities and Absolute Values sections
to the Algebra-Inequalities and Factorisation topic.
"""
from django.core.management.base import BaseCommand
from core.models import Subject
from interactive_lessons.models import Topic, Section, Question, QuestionPart


class Command(BaseCommand):
    help = "Add 3 Inequalities + 3 Absolute Values questions"

    def handle(self, *args, **options):
        topic = Topic.objects.get(slug='algebra-inequalities-and-factorisation')
        self.stdout.write(f"Topic: {topic.name} (id={topic.id})")

        sec_ineq, _ = Section.objects.get_or_create(
            name='Inequalities', topic=topic, defaults={'order': 3}
        )
        sec_abs, _ = Section.objects.get_or_create(
            name='Absolute Values', topic=topic, defaults={'order': 4}
        )

        # Check if questions already exist in these sections
        if Question.objects.filter(topic=topic, section=sec_ineq).exists():
            self.stdout.write(self.style.WARNING("Inequalities questions already exist. Skipping."))
            return
        if Question.objects.filter(topic=topic, section=sec_abs).exists():
            self.stdout.write(self.style.WARNING("Absolute Values questions already exist. Skipping."))
            return

        # ============================================================
        # INEQUALITIES - 3 questions (rational inequalities)
        # ============================================================

        # --- Ineq Q1: (4x+1)/(3x-2) >= 3 ---
        # Reformulated from: (3x-1)/(2x-3) >= 5
        # Solution: (-5x+7)/(3x-2) >= 0 => 2/3 < x <= 7/5
        q1 = Question.objects.create(
            topic=topic, order=1, section=sec_ineq,
            hint="To solve a rational inequality, bring everything to one side and combine into a single fraction. Find the critical points (where numerator = 0 and denominator = 0), then test intervals on the number line. Remember: you cannot multiply both sides by an expression containing $x$ without considering its sign.",
            is_exam_question=False, is_copyrighted=True,
        )
        QuestionPart.objects.create(
            question=q1, label="(a)", order=0,
            prompt="Find the range of values of $x$ for which\n\n$$\\frac{4x + 1}{3x - 2} \\geq 3$$\n\nwhere $x \\in \\mathbb{R}$ and $x \\neq \\frac{2}{3}$.",
            answer="2/3 < x <= 7/5",
            expected_format="Inequality (e.g., $1 < x \\leq 5$ or $x < 3$)",
            expected_type="manual", max_marks=15,
            solution="**Step 1:** Bring everything to one side:\n\n$$\\frac{4x + 1}{3x - 2} - 3 \\geq 0$$\n\n**Step 2:** Combine into a single fraction:\n\n$$\\frac{4x + 1 - 3(3x - 2)}{3x - 2} \\geq 0$$\n\n$$\\frac{4x + 1 - 9x + 6}{3x - 2} \\geq 0$$\n\n$$\\frac{-5x + 7}{3x - 2} \\geq 0$$\n\n**Step 3:** Find critical points:\n- Numerator $= 0$: $-5x + 7 = 0 \\Rightarrow x = \\frac{7}{5}$\n- Denominator $= 0$: $3x - 2 = 0 \\Rightarrow x = \\frac{2}{3}$\n\n**Step 4:** Test intervals on the number line:\n\n| Interval | $-5x+7$ | $3x-2$ | Fraction | Sign |\n|---|---|---|---|---|\n| $x < \\frac{2}{3}$ | $+$ | $-$ | $\\frac{+}{-}$ | $-$ |\n| $\\frac{2}{3} < x < \\frac{7}{5}$ | $+$ | $+$ | $\\frac{+}{+}$ | $+$ |\n| $x > \\frac{7}{5}$ | $-$ | $+$ | $\\frac{-}{+}$ | $-$ |\n\n**Step 5:** We need $\\geq 0$, so include where the fraction is positive or zero.\n\n$x = \\frac{7}{5}$ gives $0$ (included). $x = \\frac{2}{3}$ is excluded (denominator = 0).\n\n**Answer:** $\\frac{2}{3} < x \\leq \\frac{7}{5}$",
        )
        self.stdout.write(f"Created Ineq Q1 (id={q1.id})")

        # --- Ineq Q2: (5x+2)/(x-2) <= 4 ---
        # Reformulated from: (3x+1)/(x-1) <= 6
        # Solution: (x+10)/(x-2) <= 0 => -10 <= x < 2
        q2 = Question.objects.create(
            topic=topic, order=2, section=sec_ineq,
            hint="To solve a rational inequality, bring everything to one side and combine into a single fraction. Find the critical points (where numerator = 0 and denominator = 0), then test intervals on the number line.",
            is_exam_question=False, is_copyrighted=True,
        )
        QuestionPart.objects.create(
            question=q2, label="(a)", order=0,
            prompt="Solve the following inequality, for $x \\in \\mathbb{R}$, $x \\neq 2$:\n\n$$\\frac{5x + 2}{x - 2} \\leq 4$$",
            answer="-10 <= x < 2",
            expected_format="Inequality (e.g., $-3 \\leq x < 5$ or $x > 2$)",
            expected_type="manual", max_marks=15,
            solution="**Step 1:** Bring everything to one side:\n\n$$\\frac{5x + 2}{x - 2} - 4 \\leq 0$$\n\n**Step 2:** Combine into a single fraction:\n\n$$\\frac{5x + 2 - 4(x - 2)}{x - 2} \\leq 0$$\n\n$$\\frac{5x + 2 - 4x + 8}{x - 2} \\leq 0$$\n\n$$\\frac{x + 10}{x - 2} \\leq 0$$\n\n**Step 3:** Find critical points:\n- Numerator $= 0$: $x + 10 = 0 \\Rightarrow x = -10$\n- Denominator $= 0$: $x - 2 = 0 \\Rightarrow x = 2$\n\n**Step 4:** Test intervals on the number line:\n\n| Interval | $x+10$ | $x-2$ | Fraction | Sign |\n|---|---|---|---|---|\n| $x < -10$ | $-$ | $-$ | $\\frac{-}{-}$ | $+$ |\n| $-10 < x < 2$ | $+$ | $-$ | $\\frac{+}{-}$ | $-$ |\n| $x > 2$ | $+$ | $+$ | $\\frac{+}{+}$ | $+$ |\n\n**Step 5:** We need $\\leq 0$, so include where the fraction is negative or zero.\n\n$x = -10$ gives $0$ (included). $x = 2$ is excluded (denominator = 0).\n\n**Answer:** $-10 \\leq x < 2$",
        )
        self.stdout.write(f"Created Ineq Q2 (id={q2.id})")

        # --- Ineq Q3: -3 <= (2x+7)/(3x-1) ---
        # Reformulated from: -4 <= (3x+5)/(2x-3)
        # Solution: (11x+4)/(3x-1) >= 0 => x <= -4/11 or x > 1/3
        q3 = Question.objects.create(
            topic=topic, order=3, section=sec_ineq,
            hint="When the inequality has the variable expression on the right, rearrange so everything is on one side. Combine into a single fraction, find critical points, and test intervals.",
            is_exam_question=False, is_copyrighted=True,
        )
        QuestionPart.objects.create(
            question=q3, label="(a)", order=0,
            prompt="Solve the following inequality for $x \\in \\mathbb{R}$, $x \\neq \\frac{1}{3}$:\n\n$$-3 \\leq \\frac{2x + 7}{3x - 1}$$",
            answer="x <= -4/11 or x > 1/3",
            expected_format="Compound inequality (e.g., $x \\leq -2$ or $x > 3$)",
            expected_type="manual", max_marks=15,
            solution="**Step 1:** Rearrange so everything is on one side:\n\n$$\\frac{2x + 7}{3x - 1} + 3 \\geq 0$$\n\n**Step 2:** Combine into a single fraction:\n\n$$\\frac{2x + 7 + 3(3x - 1)}{3x - 1} \\geq 0$$\n\n$$\\frac{2x + 7 + 9x - 3}{3x - 1} \\geq 0$$\n\n$$\\frac{11x + 4}{3x - 1} \\geq 0$$\n\n**Step 3:** Find critical points:\n- Numerator $= 0$: $11x + 4 = 0 \\Rightarrow x = -\\frac{4}{11}$\n- Denominator $= 0$: $3x - 1 = 0 \\Rightarrow x = \\frac{1}{3}$\n\n**Step 4:** Test intervals on the number line:\n\n| Interval | $11x+4$ | $3x-1$ | Fraction | Sign |\n|---|---|---|---|---|\n| $x < -\\frac{4}{11}$ | $-$ | $-$ | $\\frac{-}{-}$ | $+$ |\n| $-\\frac{4}{11} < x < \\frac{1}{3}$ | $+$ | $-$ | $\\frac{+}{-}$ | $-$ |\n| $x > \\frac{1}{3}$ | $+$ | $+$ | $\\frac{+}{+}$ | $+$ |\n\n**Step 5:** We need $\\geq 0$, so include where the fraction is positive or zero.\n\n$x = -\\frac{4}{11}$ gives $0$ (included). $x = \\frac{1}{3}$ is excluded (denominator = 0).\n\n**Answer:** $x \\leq -\\frac{4}{11}$ or $x > \\frac{1}{3}$",
        )
        self.stdout.write(f"Created Ineq Q3 (id={q3.id})")

        # ============================================================
        # ABSOLUTE VALUES - 3 questions
        # ============================================================

        # --- Abs Q1: |x - 5| <= 8 ---
        # Reformulated from: |x - 3| <= 12
        # Solution: -3 <= x <= 13
        q4 = Question.objects.create(
            topic=topic, order=1, section=sec_abs,
            hint="For $|A| \\leq k$ where $k > 0$: the solution is $-k \\leq A \\leq k$. This means the expression inside the absolute value is trapped between $-k$ and $k$.",
            is_exam_question=False, is_copyrighted=True,
        )
        QuestionPart.objects.create(
            question=q4, label="(a)", order=0,
            prompt="Solve the following inequality for $x \\in \\mathbb{R}$:\n\n$$|x - 5| \\leq 8$$",
            answer="-3 <= x <= 13",
            expected_format="Double inequality (e.g., $-2 \\leq x \\leq 10$)",
            expected_type="manual", max_marks=10,
            solution="**Step 1:** Apply the absolute value inequality rule: $|A| \\leq k \\Rightarrow -k \\leq A \\leq k$.\n\n$$-8 \\leq x - 5 \\leq 8$$\n\n**Step 2:** Add $5$ to all three parts:\n\n$$-8 + 5 \\leq x \\leq 8 + 5$$\n\n$$-3 \\leq x \\leq 13$$\n\n**Answer:** $-3 \\leq x \\leq 13$",
        )
        self.stdout.write(f"Created Abs Q1 (id={q4.id})")

        # --- Abs Q2: |3x + 4| - 2 <= 0 ---
        # Reformulated from: |2x + 5| - 1 <= 0
        # Solution: |3x + 4| <= 2 => -2 <= 3x + 4 <= 2 => -2 <= x <= -2/3
        q5 = Question.objects.create(
            topic=topic, order=2, section=sec_abs,
            hint="First isolate the absolute value expression on one side. Then apply the rule: $|A| \\leq k \\Rightarrow -k \\leq A \\leq k$. Solve the resulting compound inequality.",
            is_exam_question=False, is_copyrighted=True,
        )
        QuestionPart.objects.create(
            question=q5, label="(a)", order=0,
            prompt="Find the range of values of $x$ for which $|3x + 4| - 2 \\leq 0$, where $x \\in \\mathbb{R}$.",
            answer="-2 <= x <= -2/3",
            expected_format="Double inequality (e.g., $-5 \\leq x \\leq 3$)",
            expected_type="manual", max_marks=10,
            solution="**Step 1:** Isolate the absolute value:\n\n$$|3x + 4| \\leq 2$$\n\n**Step 2:** Apply the rule $|A| \\leq k \\Rightarrow -k \\leq A \\leq k$:\n\n$$-2 \\leq 3x + 4 \\leq 2$$\n\n**Step 3:** Subtract $4$ from all three parts:\n\n$$-6 \\leq 3x \\leq -2$$\n\n**Step 4:** Divide all parts by $3$:\n\n$$-2 \\leq x \\leq -\\frac{2}{3}$$\n\n**Answer:** $-2 \\leq x \\leq -\\frac{2}{3}$",
        )
        self.stdout.write(f"Created Abs Q2 (id={q5.id})")

        # --- Abs Q3: |4x - 1| < 7 ---
        # New question in similar style
        # Solution: -7 < 4x - 1 < 7 => -6 < 4x < 8 => -3/2 < x < 2
        q6 = Question.objects.create(
            topic=topic, order=3, section=sec_abs,
            hint="For $|A| < k$ where $k > 0$: the solution is $-k < A < k$. Note the strict inequality (no equals sign).",
            is_exam_question=False, is_copyrighted=True,
        )
        QuestionPart.objects.create(
            question=q6, label="(a)", order=0,
            prompt="Solve the following inequality for $x \\in \\mathbb{R}$:\n\n$$|4x - 1| < 7$$",
            answer="-3/2 < x < 2",
            expected_format="Double inequality (e.g., $-1 < x < 5$)",
            expected_type="manual", max_marks=10,
            solution="**Step 1:** Apply the absolute value inequality rule: $|A| < k \\Rightarrow -k < A < k$.\n\n$$-7 < 4x - 1 < 7$$\n\n**Step 2:** Add $1$ to all three parts:\n\n$$-6 < 4x < 8$$\n\n**Step 3:** Divide all parts by $4$:\n\n$$-\\frac{3}{2} < x < 2$$\n\n**Answer:** $-\\frac{3}{2} < x < 2$",
        )
        self.stdout.write(f"Created Abs Q3 (id={q6.id})")

        self.stdout.write(self.style.SUCCESS(
            f"\nDone! Created 6 questions in Inequalities (3) and Absolute Values (3)"
        ))