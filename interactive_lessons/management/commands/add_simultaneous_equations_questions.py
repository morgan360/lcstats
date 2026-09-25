"""Add the Simultaneous Equations practice questions.

Three sections - two variables, three variables, and linear with non-linear -
of three questions each, under the topic whose slug is
algebra-inequalities-and-factorisation (named "Algebra-Simultaneous
Equations_Inequalities..." on production).

Content authored on local and replayed here so production gets exactly what was
tested. Idempotent: keyed on topic slug, section name and question order rather
than primary key, because ids differ between local and production. Re-running
updates in place and never duplicates.

Each unknown gets its own part with a bare-number answer. The numeric grader
strips "x" and "=" but not "y" or "z", so a combined answer such as
"x=2, y=3" would lose its y value and mark any y as correct.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Subject
from interactive_lessons.models import Topic, Question, QuestionPart, Section

TOPIC_SLUG = "algebra-inequalities-and-factorisation"
TOPIC_NAME = "Algebra-Inequalities and Factorisation"
SUBJECT_NAME = "Maths"
PAPER = "p1"

HINT_TWO = r"""**Elimination:** multiply one or both equations so that one variable has equal (or opposite) coefficients, then subtract (or add) to remove it. Solve for the remaining variable and substitute back into either original equation to find the other. Clear any fractions first by multiplying each equation by the LCM of its denominators."""

HINT_THREE = r"""**Three unknowns:** use two different pairs of equations to eliminate the **same** variable, giving two equations in two unknowns. Solve those, then substitute both values into any original equation to find the third. Clear fractions first, and always check your answers in the equation you did not use last."""

HINT_NONLINEAR = r"""**Substitution:** rearrange the **linear** equation to make one variable the subject, then substitute into the non-linear equation. This gives a quadratic in one variable: solve it, then substitute **each** root back into the *linear* equation to find the matching value of the other variable. There are usually two solution pairs."""


def part(label, order, prompt, answer, expected_format, max_marks, solution):
    return {
        "label": label,
        "order": order,
        "prompt": prompt,
        "answer": answer,
        "expected_format": expected_format,
        "expected_type": "numeric",
        "max_marks": max_marks,
        "unlock": 2,
        "scale": None,
        "solution": solution,
        "qk": False,
    }


def question(order, hint, parts):
    return {
        "order": order,
        "hint": hint,
        "solution": None,
        "is_copyrighted": True,
        "is_exam_question": False,
        "is_quickkick_suitable": False,
        "parts": parts,
    }


ONE_VALUE = "Single value (e.g., 6 or -2)"

# (section name, section order, [questions])
QUESTIONS = [
    ("""Simultaneous Equations (2 Variables)""", 5, [
        question(1, HINT_TWO, [
            part("(a)", 0, r"""Solve the simultaneous equations

$$5x - 3y = 29$$

$$2x + 7y = -13$$

Find the value of $x$.""", "4", ONE_VALUE, 10, r"""**Step 1:** Label the equations.

$$5x - 3y = 29 \quad (1)$$

$$2x + 7y = -13 \quad (2)$$

**Step 2:** Make the $y$ coefficients opposite. Multiply $(1)$ by $7$ and $(2)$ by $3$:

$$35x - 21y = 203$$

$$6x + 21y = -39$$

**Step 3:** Add to eliminate $y$:

$$41x = 164$$

$$x = 4$$

**Answer:** $x = 4$"""),
            part("(b)", 1, r"""Hence find the value of $y$.""", "-3", ONE_VALUE, 5, r"""**Step 1:** Substitute $x = 4$ into $(1)$:

$$5(4) - 3y = 29$$

$$20 - 3y = 29$$

$$-3y = 9$$

$$y = -3$$

**Step 2:** Check in $(2)$: $2(4) + 7(-3) = 8 - 21 = -13$ ✓

**Answer:** $y = -3$"""),
        ]),
        question(2, HINT_TWO, [
            part("(a)", 0, r"""Solve the simultaneous equations

$$\frac{x}{2} + \frac{2y}{3} = 4$$

$$\frac{3x}{4} - \frac{y}{5} = -\frac{24}{5}$$

Find the value of $x$.""", "-4", ONE_VALUE, 10, r"""**Step 1:** Clear the fractions. Multiply the first equation by $6$ and the second by $20$:

$$3x + 4y = 24 \quad (1)$$

$$15x - 4y = -96 \quad (2)$$

**Step 2:** The $y$ coefficients are already opposite. Add $(1)$ and $(2)$:

$$18x = -72$$

$$x = -4$$

**Answer:** $x = -4$"""),
            part("(b)", 1, r"""Hence find the value of $y$.""", "9", ONE_VALUE, 5, r"""**Step 1:** Substitute $x = -4$ into $(1)$:

$$3(-4) + 4y = 24$$

$$4y = 36$$

$$y = 9$$

**Step 2:** Check in the original second equation:

$$\frac{3(-4)}{4} - \frac{9}{5} = -3 - \frac{9}{5} = -\frac{24}{5} \checkmark$$

**Answer:** $y = 9$"""),
        ]),
        question(3, HINT_TWO, [
            part("(a)", 0, r"""Solve the simultaneous equations

$$\frac{x + 2}{3} - \frac{y - 1}{4} = 2$$

$$\frac{x - 2}{5} + \frac{y + 3}{2} = 5$$

Find the value of $y$.""", "5", ONE_VALUE, 10, r"""**Step 1:** Multiply the first equation by $12$:

$$4(x + 2) - 3(y - 1) = 24$$

$$4x + 8 - 3y + 3 = 24$$

$$4x - 3y = 13 \quad (1)$$

**Step 2:** Multiply the second equation by $10$:

$$2(x - 2) + 5(y + 3) = 50$$

$$2x - 4 + 5y + 15 = 50$$

$$2x + 5y = 39 \quad (2)$$

**Step 3:** Multiply $(2)$ by $2$ and subtract $(1)$:

$$4x + 10y = 78$$

$$(4x + 10y) - (4x - 3y) = 78 - 13$$

$$13y = 65$$

$$y = 5$$

**Answer:** $y = 5$"""),
            part("(b)", 1, r"""Hence find the value of $x$.""", "7", ONE_VALUE, 5, r"""**Step 1:** Substitute $y = 5$ into $(2)$:

$$2x + 5(5) = 39$$

$$2x = 14$$

$$x = 7$$

**Step 2:** Check in the original first equation:

$$\frac{7 + 2}{3} - \frac{5 - 1}{4} = 3 - 1 = 2 \checkmark$$

**Answer:** $x = 7$"""),
        ]),
    ]),
    ("""Simultaneous Equations (3 Variables)""", 6, [
        question(1, HINT_THREE, [
            part("(a)", 0, r"""Solve the simultaneous equations

$$x + 2y + 3z = 9$$

$$3x - y + 2z = 13$$

$$2x + 3y - z = -2$$

Find the value of $x$.""", "2", ONE_VALUE, 10, r"""**Step 1:** Label the equations.

$$x + 2y + 3z = 9 \quad (1)$$

$$3x - y + 2z = 13 \quad (2)$$

$$2x + 3y - z = -2 \quad (3)$$

**Step 2:** Eliminate $z$ using $(1)$ and $(3)$. Add $(1)$ to $3 \times (3)$:

$$x + 2y + 3z + 6x + 9y - 3z = 9 - 6$$

$$7x + 11y = 3 \quad (4)$$

**Step 3:** Eliminate $z$ using $(2)$ and $(3)$. Add $(2)$ to $2 \times (3)$:

$$3x - y + 2z + 4x + 6y - 2z = 13 - 4$$

$$7x + 5y = 9 \quad (5)$$

**Step 4:** Subtract $(5)$ from $(4)$:

$$6y = -6 \Rightarrow y = -1$$

**Step 5:** Substitute into $(5)$:

$$7x + 5(-1) = 9$$

$$7x = 14$$

$$x = 2$$

**Answer:** $x = 2$"""),
            part("(b)", 1, r"""Find the value of $y$.""", "-1", ONE_VALUE, 5, r"""**Step 1:** From part (a), subtracting $(5)$ from $(4)$ gave

$$6y = -6$$

$$y = -1$$

**Answer:** $y = -1$"""),
            part("(c)", 2, r"""Find the value of $z$.""", "3", ONE_VALUE, 5, r"""**Step 1:** Substitute $x = 2$ and $y = -1$ into $(1)$:

$$2 + 2(-1) + 3z = 9$$

$$3z = 9$$

$$z = 3$$

**Step 2:** Check in $(2)$: $3(2) - (-1) + 2(3) = 6 + 1 + 6 = 13$ ✓

**Answer:** $z = 3$"""),
        ]),
        question(2, HINT_THREE, [
            part("(a)", 0, r"""Solve the simultaneous equations

$$\frac{x}{5} + \frac{y}{2} - \frac{z}{3} = 3$$

$$2x + 3y + z = 13$$

$$4x - 2y - 3z = 25$$

Find the value of $x$.""", "5", ONE_VALUE, 10, r"""**Step 1:** Clear the fractions. Multiply the first equation by $30$:

$$6x + 15y - 10z = 90 \quad (1)$$

$$2x + 3y + z = 13 \quad (2)$$

$$4x - 2y - 3z = 25 \quad (3)$$

**Step 2:** Eliminate $z$. Add $(1)$ to $10 \times (2)$:

$$6x + 15y - 10z + 20x + 30y + 10z = 90 + 130$$

$$26x + 45y = 220 \quad (4)$$

**Step 3:** Eliminate $z$ again. Add $(3)$ to $3 \times (2)$:

$$4x - 2y - 3z + 6x + 9y + 3z = 25 + 39$$

$$10x + 7y = 64 \quad (5)$$

**Step 4:** Eliminate $y$. Multiply $(4)$ by $7$ and $(5)$ by $45$:

$$182x + 315y = 1540$$

$$450x + 315y = 2880$$

Subtract:

$$268x = 1340$$

$$x = 5$$

**Answer:** $x = 5$"""),
            part("(b)", 1, r"""Find the value of $y$.""", "2", ONE_VALUE, 5, r"""**Step 1:** Substitute $x = 5$ into $(5)$:

$$10(5) + 7y = 64$$

$$7y = 14$$

$$y = 2$$

**Answer:** $y = 2$"""),
            part("(c)", 2, r"""Find the value of $z$.""", "-3", ONE_VALUE, 5, r"""**Step 1:** Substitute $x = 5$ and $y = 2$ into $(2)$:

$$2(5) + 3(2) + z = 13$$

$$16 + z = 13$$

$$z = -3$$

**Step 2:** Check in the original first equation:

$$\frac{5}{5} + \frac{2}{2} - \frac{-3}{3} = 1 + 1 + 1 = 3 \checkmark$$

**Answer:** $z = -3$"""),
        ]),
        question(3, HINT_THREE + r""" For the **"hence"** part, compare the second system with the first term by term: each bracketed expression plays the role of one of $x$, $y$ or $z$.""", [
            part("(a)", 0, r"""Solve the simultaneous equations

$$x + y + z = 8$$

$$2x + 3y - z = 11$$

$$x - 2y + 4z = 17$$

Find the value of $x$.""", "9", ONE_VALUE, 10, r"""**Step 1:** Label the equations.

$$x + y + z = 8 \quad (1)$$

$$2x + 3y - z = 11 \quad (2)$$

$$x - 2y + 4z = 17 \quad (3)$$

**Step 2:** Eliminate $z$. Add $(1)$ and $(2)$:

$$3x + 4y = 19 \quad (4)$$

**Step 3:** Eliminate $z$ again. Add $4 \times (2)$ to $(3)$:

$$8x + 12y - 4z + x - 2y + 4z = 44 + 17$$

$$9x + 10y = 61 \quad (5)$$

**Step 4:** Multiply $(4)$ by $3$ and subtract from $(5)$:

$$9x + 12y = 57$$

$$(9x + 10y) - (9x + 12y) = 61 - 57$$

$$-2y = 4 \Rightarrow y = -2$$

**Step 5:** Substitute into $(4)$:

$$3x + 4(-2) = 19$$

$$3x = 27$$

$$x = 9$$

**Answer:** $x = 9$"""),
            part("(b)", 1, r"""Find the value of $y$.""", "-2", ONE_VALUE, 5, r"""**Step 1:** From part (a), $(5) - 3 \times (4)$ gave

$$-2y = 4$$

$$y = -2$$

**Answer:** $y = -2$"""),
            part("(c)", 2, r"""Find the value of $z$.""", "1", ONE_VALUE, 5, r"""**Step 1:** Substitute $x = 9$ and $y = -2$ into $(1)$:

$$9 - 2 + z = 8$$

$$z = 1$$

**Step 2:** Check in $(3)$: $9 - 2(-2) + 4(1) = 9 + 4 + 4 = 17$ ✓

**Answer:** $z = 1$"""),
            part("(d)", 3, r"""**Hence**, solve

$$a^2 + b + (c + 2) = 8$$

$$2a^2 + 3b - (c + 2) = 11$$

$$a^2 - 2b + 4(c + 2) = 17$$

Find all possible values of $a$.""", "3,-3", "Two values separated by a comma (e.g., 5,-5 or 2,-2)", 5, r"""**Step 1:** Compare with the first system. The equations are identical with

$$x = a^2, \quad y = b, \quad z = c + 2$$

**Step 2:** From part (a), $x = 9$, so

$$a^2 = 9$$

$$a = 3 \text{ or } a = -3$$

**Answer:** $a = \pm 3$"""),
            part("(e)", 4, r"""Find the value of $c$.""", "-1", ONE_VALUE, 5, r"""**Step 1:** From part (c), $z = 1$, and $z = c + 2$:

$$c + 2 = 1$$

$$c = -1$$

(Similarly $b = y = -2$.)

**Answer:** $c = -1$"""),
        ]),
    ]),
    ("""Linear and Non-Linear Simultaneous Equations""", 7, [
        question(1, HINT_NONLINEAR, [
            part("(a)", 0, r"""Solve the simultaneous equations

$$x + 2y = 5$$

$$x^2 + y^2 = 10$$

Find the two values of $y$.""", "1,3", "Two values separated by a comma (e.g., -2,5)", 15, r"""**Step 1:** Make $x$ the subject of the linear equation:

$$x = 5 - 2y$$

**Step 2:** Substitute into $x^2 + y^2 = 10$:

$$(5 - 2y)^2 + y^2 = 10$$

$$25 - 20y + 4y^2 + y^2 = 10$$

$$5y^2 - 20y + 15 = 0$$

**Step 3:** Divide by $5$ and factorise:

$$y^2 - 4y + 3 = 0$$

$$(y - 1)(y - 3) = 0$$

$$y = 1 \text{ or } y = 3$$

**Answer:** $y = 1$ or $y = 3$"""),
            part("(b)", 1, r"""Find the corresponding values of $x$.""", "3,-1", "Two values separated by a comma, in the same order as your $y$ values (e.g., 4,-2)", 10, r"""**Step 1:** Substitute each $y$ into the linear equation $x = 5 - 2y$:

$$y = 1: \quad x = 5 - 2 = 3$$

$$y = 3: \quad x = 5 - 6 = -1$$

**Step 2:** Check $(-1, 3)$ in the circle: $(-1)^2 + 3^2 = 1 + 9 = 10$ ✓

**Answer:** $x = 3$ (when $y = 1$) and $x = -1$ (when $y = 3$), giving the points $(3, 1)$ and $(-1, 3)$"""),
        ]),
        question(2, HINT_NONLINEAR, [
            part("(a)", 0, r"""Solve the simultaneous equations

$$x + 3y = 7$$

$$xy = 4$$

Find the two values of $y$.""", "1,4/3", "Two values separated by a comma, fractions allowed (e.g., 2,5/2)", 15, r"""**Step 1:** Make $x$ the subject of the linear equation:

$$x = 7 - 3y$$

**Step 2:** Substitute into $xy = 4$:

$$(7 - 3y)y = 4$$

$$7y - 3y^2 = 4$$

$$3y^2 - 7y + 4 = 0$$

**Step 3:** Factorise:

$$(3y - 4)(y - 1) = 0$$

$$y = \frac{4}{3} \text{ or } y = 1$$

**Answer:** $y = 1$ or $y = \frac{4}{3}$"""),
            part("(b)", 1, r"""Find the corresponding values of $x$.""", "4,3", "Two values separated by a comma, in the same order as your $y$ values (e.g., 6,-1)", 10, r"""**Step 1:** Substitute each $y$ into $x = 7 - 3y$:

$$y = 1: \quad x = 7 - 3 = 4$$

$$y = \frac{4}{3}: \quad x = 7 - 4 = 3$$

**Step 2:** Check in $xy = 4$: $4 \times 1 = 4$ ✓ and $3 \times \frac{4}{3} = 4$ ✓

**Answer:** $x = 4$ (when $y = 1$) and $x = 3$ (when $y = \frac{4}{3}$)"""),
        ]),
        question(3, HINT_NONLINEAR, [
            part("(a)", 0, r"""Solve the simultaneous equations

$$\frac{x}{5} - \frac{y}{10} = 1$$

$$x^2 + y^2 - 4x + 2y - 20 = 0$$

Find the two values of $x$.""", "2,6", "Two values separated by a comma (e.g., -3,4)", 15, r"""**Step 1:** Multiply the linear equation by $10$ and make $y$ the subject:

$$2x - y = 10$$

$$y = 2x - 10$$

**Step 2:** Substitute into the circle:

$$x^2 + (2x - 10)^2 - 4x + 2(2x - 10) - 20 = 0$$

$$x^2 + 4x^2 - 40x + 100 - 4x + 4x - 20 - 20 = 0$$

$$5x^2 - 40x + 60 = 0$$

**Step 3:** Divide by $5$ and factorise:

$$x^2 - 8x + 12 = 0$$

$$(x - 2)(x - 6) = 0$$

$$x = 2 \text{ or } x = 6$$

**Answer:** $x = 2$ or $x = 6$"""),
            part("(b)", 1, r"""Find the corresponding values of $y$.""", "-6,2", "Two values separated by a comma, in the same order as your $x$ values (e.g., 3,-5)", 10, r"""**Step 1:** Substitute each $x$ into $y = 2x - 10$:

$$x = 2: \quad y = 4 - 10 = -6$$

$$x = 6: \quad y = 12 - 10 = 2$$

**Step 2:** Check $(6, 2)$ in the circle: $36 + 4 - 24 + 4 - 20 = 0$ ✓

**Answer:** $y = -6$ (when $x = 2$) and $y = 2$ (when $x = 6$), giving the points $(2, -6)$ and $(6, 2)$"""),
        ]),
    ]),
]


class Command(BaseCommand):
    help = "Add or update the Simultaneous Equations practice questions"

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
            # Keyed on slug only: production has renamed this topic, and the
            # name in defaults applies only if the topic does not exist yet.
            topic, created = Topic.objects.get_or_create(
                slug=TOPIC_SLUG,
                defaults={"name": TOPIC_NAME, "subject": subject, "paper": PAPER},
            )
            self.stdout.write(f'{"Created" if created else "Found"} topic "{topic.name}"')

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

                    question_obj, made = Question.objects.update_or_create(
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
                        f'    {"created" if made else "updated"} question {question_obj.order}'
                    )

                    for p in entry["parts"]:
                        QuestionPart.objects.update_or_create(
                            question=question_obj,
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
