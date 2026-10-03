"""Add the Geometry-Theorems practice questions: four Warm-up, four Workout, four Stretch.

Content authored on local and replayed here so production gets exactly what was
tested. Idempotent: keyed on topic slug, section name and question order rather
than primary key, because ids differ between local and production. Re-running
updates in place and never duplicates.

The questions apply Theorems 1-19 rather than prove them: each answer is a
number, and every solution names the theorem behind each step, so students see
the "giving a reason" habit Paper 2 Q6 rewards. The examinable proofs are left
to the Proof Jigsaw flashcards.

Angles are stored as bare numbers. The grader accepts them with or without a
degree sign (compare_ignoring_one_sided_degrees in stats_tutor).

Eleven part (a)s carry a diagram from scripts/geometry_theorem_diagrams.py.
Images live in media/, which git does not carry, so copy
media/question_part_images/geo_*.png to production before running this there; a
missing file is reported and skipped rather than attached as a broken image.
"""
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Subject
from interactive_lessons.models import Topic, Question, QuestionPart, Section

TOPIC_SLUG = "geometry-theorems"
TOPIC_NAME = "Angles, Lines & Triangles"
SUBJECT_NAME = "Maths"
PAPER = "p2"

DEGREES = "Number of degrees (e.g., 72)"
LENGTH = "Number only (e.g., 7.5)"
WHOLE = "Whole number only (e.g., 9)"

# (section name, section order, [questions])
QUESTIONS = [
    ("""Warm-up""", 1, [
        {
            "order": 1,
            "hint": r"""**Theorem 1:** vertically opposite angles are equal. Angles on a straight line add to $180^\circ$.""",
            "parts": [
                {
                    "label": "(a)",
                    "image": "question_part_images/geo_easy1_crossing_lines.png",
                    "prompt": r"""Two straight lines cross as shown.

Find the value of $x$.""",
                    "answer": "20",
                    "expected_format": WHOLE,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** The angles $(3x+10)^\circ$ and $(5x-30)^\circ$ are vertically opposite, so they are equal (**Theorem 1**):

$$3x + 10 = 5x - 30$$

**Step 2:** Solve:

$$40 = 2x \quad\Rightarrow\quad x = 20$$

**Answer:** $x = 20$""",
                },
                {
                    "label": "(b)",
                    "prompt": r"""Find the value of $y$.""",
                    "answer": "110",
                    "expected_format": DEGREES,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** With $x = 20$, the marked angle is $3(20) + 10 = 70^\circ$.

**Step 2:** $y^\circ$ and $70^\circ$ lie together on a straight line, so they add to $180^\circ$:

$$y = 180 - 70 = 110$$

**Answer:** $y = 110$""",
                },
            ],
        },
        {
            "order": 2,
            "hint": r"""**Theorem 2:** in an isosceles triangle the angles opposite the equal sides are equal. **Theorem 4:** the angles in a triangle add to $180^\circ$.""",
            "parts": [
                {
                    "label": "(a)",
                    "image": "question_part_images/geo_easy2_isosceles.png",
                    "prompt": r"""In the triangle $ABC$, $|AB| = |AC|$ and $|\angle BAC| = 42^\circ$. The side $[BC]$ is extended to $D$.

Find $|\angle ABC|$.""",
                    "answer": "69",
                    "expected_format": DEGREES,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** $|AB| = |AC|$, so the angles opposite those sides are equal (**Theorem 2**): $|\angle ABC| = |\angle ACB|$.

**Step 2:** The angles in the triangle add to $180^\circ$ (**Theorem 4**):

$$42 + 2|\angle ABC| = 180 \quad\Rightarrow\quad |\angle ABC| = \frac{138}{2} = 69$$

**Answer:** $69^\circ$""",
                },
                {
                    "label": "(b)",
                    "prompt": r"""Find $|\angle ACD|$.""",
                    "answer": "111",
                    "expected_format": DEGREES,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Method 1:** $\angle ACD$ is an exterior angle of the triangle, so it equals the sum of the two interior opposite angles (**Theorem 6**):

$$|\angle ACD| = 42 + 69 = 111$$

**Method 2:** $|\angle ACB| = 69^\circ$, and $\angle ACB$, $\angle ACD$ lie on a straight line: $180 - 69 = 111$.

**Answer:** $111^\circ$""",
                },
            ],
        },
        {
            "order": 3,
            "hint": r"""When a transversal cuts two **parallel** lines, alternate angles are equal (**Theorem 3**) and corresponding angles are equal (**Theorem 5**). Angles on a straight line add to $180^\circ$.""",
            "parts": [
                {
                    "label": "(a)",
                    "image": "question_part_images/geo_easy3_parallel_lines.png",
                    "prompt": r"""The lines $l$ and $m$ are parallel. A transversal cuts $l$ at $P$ and $m$ at $Q$.

Find the angle $a$.""",
                    "answer": "65",
                    "expected_format": DEGREES,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** The $65^\circ$ angle at $P$ and the angle $a$ at $Q$ lie on opposite sides of the transversal, between the two lines: they are **alternate angles**.

**Step 2:** $l \parallel m$, so alternate angles are equal (**Theorem 3**):

$$a = 65^\circ$$

**Answer:** $65^\circ$""",
                },
                {
                    "label": "(b)",
                    "prompt": r"""Find the angle $b$.""",
                    "answer": "115",
                    "expected_format": DEGREES,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** $a$ and $b$ together make a straight angle along the line $m$:

$$a + b = 180^\circ$$

**Step 2:** $b = 180 - 65 = 115$.

**Answer:** $115^\circ$

*Note:* $b$ and the $65^\circ$ angle are on the same side of the transversal, between the parallel lines. Such angles always add to $180^\circ$.""",
                },
            ],
        },
        {
            "order": 4,
            "hint": r"""**Theorem 6:** an exterior angle of a triangle equals the sum of the two interior opposite angles.""",
            "parts": [
                {
                    "label": "(a)",
                    "image": "question_part_images/geo_easy4_exterior_angle.png",
                    "prompt": r"""In the triangle $ABC$, $|\angle BAC| = x^\circ$ and $|\angle ABC| = 2x^\circ$. The side $[BC]$ is extended to $D$, and $|\angle ACD| = 126^\circ$.

Find the value of $x$.""",
                    "answer": "42",
                    "expected_format": WHOLE,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** $\angle ACD$ is an exterior angle, so it equals the sum of the interior opposite angles at $A$ and $B$ (**Theorem 6**):

$$x + 2x = 126$$

**Step 2:** $3x = 126 \Rightarrow x = 42$.

**Answer:** $x = 42$""",
                },
                {
                    "label": "(b)",
                    "prompt": r"""Find $|\angle ACB|$.""",
                    "answer": "54",
                    "expected_format": DEGREES,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** $\angle ACB$ and $\angle ACD$ lie on a straight line:

$$|\angle ACB| = 180 - 126 = 54$$

**Check (Theorem 4):** $42 + 84 + 54 = 180$ ✓

**Answer:** $54^\circ$""",
                },
            ],
        },
    ]),
    ("""Workout""", 2, [
        {
            "order": 1,
            "hint": r"""In a parallelogram, opposite angles are equal (**Theorem 9**) and the diagonals bisect each other (**Theorem 10**). Neighbouring angles add to $180^\circ$, because the sides are parallel.""",
            "parts": [
                {
                    "label": "(a)",
                    "image": "question_part_images/geo_medium1_parallelogram.png",
                    "prompt": r"""$ABCD$ is a parallelogram with $|\angle DAB| = (3y - 20)^\circ$ and $|\angle BCD| = (2y + 15)^\circ$.

Find the value of $y$.""",
                    "answer": "35",
                    "expected_format": WHOLE,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** $\angle DAB$ and $\angle BCD$ are opposite angles of the parallelogram, so they are equal (**Theorem 9**):

$$3y - 20 = 2y + 15$$

**Step 2:** $y = 35$.

**Answer:** $y = 35$""",
                },
                {
                    "label": "(b)",
                    "prompt": r"""Find $|\angle ABC|$.""",
                    "answer": "95",
                    "expected_format": DEGREES,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** $|\angle DAB| = 3(35) - 20 = 85^\circ$.

**Step 2:** $AD \parallel BC$, so $\angle DAB$ and $\angle ABC$ are on the same side of the transversal $AB$, between parallel lines, and they add to $180^\circ$:

$$|\angle ABC| = 180 - 85 = 95$$

**Answer:** $95^\circ$""",
                },
                {
                    "label": "(c)",
                    "prompt": r"""The diagonals meet at $E$. Given that $|AE| = 3t - 2$ and $|EC| = t + 6$, find $|AC|$.""",
                    "answer": "20",
                    "expected_format": LENGTH,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** The diagonals of a parallelogram bisect each other (**Theorem 10**), so $|AE| = |EC|$:

$$3t - 2 = t + 6 \quad\Rightarrow\quad t = 4$$

**Step 2:** $|AE| = |EC| = 10$, so $|AC| = 10 + 10 = 20$.

**Answer:** $20$""",
                },
            ],
        },
        {
            "order": 2,
            "hint": r"""**Theorem 12:** a line parallel to one side of a triangle cuts the other two sides in the same ratio. **Theorem 13:** similar triangles have proportional sides. Match the sides in order.""",
            "parts": [
                {
                    "label": "(a)",
                    "image": "question_part_images/geo_medium2_parallel_in_triangle.png",
                    "prompt": r"""In the triangle $ABC$, $X$ is on $[AB]$ and $Y$ is on $[AC]$, with $XY \parallel BC$.

$|AX| = 6$, $|XB| = 4$, $|AY| = 9$ and $|XY| = 9$.

Find $|YC|$.""",
                    "answer": "6",
                    "expected_format": LENGTH,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** $XY \parallel BC$, so $XY$ cuts $[AB]$ and $[AC]$ in the same ratio (**Theorem 12**):

$$\frac{|AX|}{|XB|} = \frac{|AY|}{|YC|}$$

**Step 2:** Substitute:

$$\frac{6}{4} = \frac{9}{|YC|} \quad\Rightarrow\quad |YC| = \frac{9 \times 4}{6} = 6$$

**Answer:** $6$""",
                },
                {
                    "label": "(b)",
                    "prompt": r"""Find $|BC|$.""",
                    "answer": "15",
                    "expected_format": LENGTH,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** The triangles $AXY$ and $ABC$ are similar: they share the angle at $A$, and $|\angle AXY| = |\angle ABC|$ because these are corresponding angles on parallel lines (**Theorem 5**).

**Step 2:** Similar triangles have proportional sides, in order (**Theorem 13**):

$$\frac{|BC|}{|XY|} = \frac{|AB|}{|AX|} = \frac{10}{6}$$

**Step 3:** $|BC| = 9 \times \dfrac{10}{6} = 15$.

**Answer:** $15$

*Watch out:* Theorem 12 compares $|AX|$ with $|XB|$, but $XY$ and $BC$ are compared using the **whole** side $|AB| = 10$.""",
                },
            ],
        },
        {
            "order": 3,
            "hint": r"""First show the two triangles are similar: look for a pair of **vertically opposite** angles and a pair of **alternate** angles. Then match the sides in order.""",
            "parts": [
                {
                    "label": "(a)",
                    "image": "question_part_images/geo_medium3_bow_tie.png",
                    "prompt": r"""The line segments $[AE]$ and $[BD]$ cross at $C$, and $AB \parallel DE$.

$|CA| = 4$, $|CB| = 5$, $|AB| = 6$ and $|CE| = 10$.

Find $|DE|$.""",
                    "answer": "15",
                    "expected_format": LENGTH,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** Show the triangles $ABC$ and $EDC$ are similar:
- $|\angle ACB| = |\angle ECD|$: vertically opposite (**Theorem 1**)
- $|\angle BAC| = |\angle DEC|$: alternate angles, since $AB \parallel DE$ (**Theorem 3**)

So $A \leftrightarrow E$, $B \leftrightarrow D$, $C \leftrightarrow C$.

**Step 2:** The sides are proportional, in order (**Theorem 13**). The scale factor is $\dfrac{|CE|}{|CA|} = \dfrac{10}{4} = 2.5$.

**Step 3:** $|DE| = 2.5 \times |AB| = 2.5 \times 6 = 15$.

**Answer:** $15$""",
                },
                {
                    "label": "(b)",
                    "prompt": r"""Find $|CD|$.""",
                    "answer": "12.5",
                    "expected_format": LENGTH,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** $D$ matches $B$, so $[CD]$ matches $[CB]$.

**Step 2:** $|CD| = 2.5 \times |CB| = 2.5 \times 5 = 12.5$.

**Answer:** $12.5$""",
                },
            ],
        },
        {
            "order": 4,
            "hint": r"""**Theorem 15** (the converse of Pythagoras): if $a^2 + b^2 = c^2$, the angle opposite $c$ is a right angle. **Theorem 14** (Pythagoras): in a right-angled triangle, $c^2 = a^2 + b^2$.""",
            "parts": [
                {
                    "label": "(a)",
                    "image": "question_part_images/geo_medium4_quadrilateral.png",
                    "prompt": r"""In the quadrilateral $ABCD$, $|AB| = 7$, $|BC| = 24$ and $|AC| = 25$. Also $|\angle ACD| = 90^\circ$ and $|CD| = 60$.

Find $|\angle ABC|$.""",
                    "answer": "90",
                    "expected_format": DEGREES,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** Test the sides of the triangle $ABC$:

$$|AB|^2 + |BC|^2 = 49 + 576 = 625 = 25^2 = |AC|^2$$

**Step 2:** The square of one side equals the sum of the squares of the other two, so the angle opposite $[AC]$ is a right angle (**Theorem 15**).

**Answer:** $|\angle ABC| = 90^\circ$""",
                },
                {
                    "label": "(b)",
                    "prompt": r"""Find $|AD|$.""",
                    "answer": "65",
                    "expected_format": LENGTH,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** The triangle $ACD$ is right-angled at $C$, so $[AD]$ is the hypotenuse (**Theorem 14**):

$$|AD|^2 = |AC|^2 + |CD|^2 = 625 + 3600 = 4225$$

**Step 2:** $|AD| = \sqrt{4225} = 65$.

**Answer:** $65$""",
                },
            ],
        },
    ]),
    ("""Stretch""", 3, [
        {
            "order": 1,
            "hint": r"""**Theorem 19:** the angle at the centre is twice the angle at the circumference standing on the same arc. Any two radii make an isosceles triangle.""",
            "parts": [
                {
                    "label": "(a)",
                    "image": "question_part_images/geo_hard1_centre_angle.png",
                    "prompt": r"""$A$, $B$ and $C$ are points on a circle with centre $O$, and $|\angle ACB| = 38^\circ$.

Find $|\angle AOB|$.""",
                    "answer": "76",
                    "expected_format": DEGREES,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** $\angle AOB$ (at the centre) and $\angle ACB$ (at the circumference) both stand on the arc $AB$.

**Step 2:** The angle at the centre is twice the angle at the circumference (**Theorem 19**):

$$|\angle AOB| = 2 \times 38 = 76$$

**Answer:** $76^\circ$""",
                },
                {
                    "label": "(b)",
                    "prompt": r"""Find $|\angle OAB|$.""",
                    "answer": "52",
                    "expected_format": DEGREES,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** $|OA| = |OB|$ (both radii), so the triangle $OAB$ is isosceles and $|\angle OAB| = |\angle OBA|$ (**Theorem 2**).

**Step 2:** The angles in the triangle add to $180^\circ$ (**Theorem 4**):

$$|\angle OAB| = \frac{180 - 76}{2} = 52$$

**Answer:** $52^\circ$""",
                },
            ],
        },
        {
            "order": 2,
            "hint": r"""Draw on the radius $[OC]$: it splits the figure into two isosceles triangles. Then use **Theorem 19** on the arc $AB$.""",
            "parts": [
                {
                    "label": "(a)",
                    "image": "question_part_images/geo_hard2_two_isosceles.png",
                    "prompt": r"""$A$, $B$ and $C$ are points on a circle with centre $O$. $|\angle OCA| = 25^\circ$ and $|\angle OCB| = 30^\circ$.

Find $|\angle ACB|$.""",
                    "answer": "55",
                    "expected_format": DEGREES,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** The radius $[OC]$ lies inside $\angle ACB$ and splits it in two:

$$|\angle ACB| = |\angle OCA| + |\angle OCB| = 25 + 30 = 55$$

**Answer:** $55^\circ$""",
                },
                {
                    "label": "(b)",
                    "prompt": r"""Find $|\angle AOB|$.""",
                    "answer": "110",
                    "expected_format": DEGREES,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** $\angle AOB$ and $\angle ACB$ stand on the same arc $AB$.

**Step 2:** The angle at the centre is twice the angle at the circumference (**Theorem 19**):

$$|\angle AOB| = 2 \times 55 = 110$$

**Check:** $|OA| = |OC|$, so $|\angle OAC| = 25^\circ$ and $|\angle AOC| = 130^\circ$. Likewise $|\angle BOC| = 120^\circ$. Then $130 + 120 + 110 = 360$ ✓

**Answer:** $110^\circ$""",
                },
                {
                    "label": "(c)",
                    "prompt": r"""Find $|\angle OAB|$.""",
                    "answer": "35",
                    "expected_format": DEGREES,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** $|OA| = |OB|$ (radii), so the triangle $OAB$ is isosceles (**Theorem 2**).

**Step 2:** **Theorem 4**:

$$|\angle OAB| = \frac{180 - 110}{2} = 35$$

**Answer:** $35^\circ$""",
                },
            ],
        },
        {
            "order": 3,
            "hint": r"""Area of a parallelogram $=$ base $\times$ perpendicular height (**Theorem 18**), and a diagonal cuts it into two equal halves (**Theorem 17**). The area is the same whichever side you take as the base (**Theorem 16**).""",
            "parts": [
                {
                    "label": "(a)",
                    "image": "question_part_images/geo_hard3_parallelogram_area.png",
                    "prompt": r"""$ABCD$ is a parallelogram with $|AB| = 12$ and $|AD| = 7.5$. The perpendicular distance between $AB$ and $DC$ is $5$.

Find the area of $ABCD$.""",
                    "answer": "60",
                    "expected_format": LENGTH,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** Area $=$ base $\times$ perpendicular height (**Theorem 18**).

**Step 2:** Using the base $[AB]$: area $= 12 \times 5 = 60$.

*Note:* $7.5$ is the slanted side, **not** the height.

**Answer:** $60$""",
                },
                {
                    "label": "(b)",
                    "prompt": r"""Find the area of the triangle $ABD$.""",
                    "answer": "30",
                    "expected_format": LENGTH,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** The diagonal $[BD]$ bisects the area of the parallelogram (**Theorem 17**).

**Step 2:** Area of $ABD = \dfrac{60}{2} = 30$.

**Answer:** $30$""",
                },
                {
                    "label": "(c)",
                    "prompt": r"""Find the perpendicular distance from $B$ to the line $AD$.""",
                    "answer": "8",
                    "expected_format": LENGTH,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** Take $[AD]$ as the base instead. The area is still $60$ (**Theorem 16**: base $\times$ height does not depend on the choice of base). The height to $AD$ is the distance from $B$ to that line, $h$:

$$7.5 \times h = 60$$

**Step 2:** $h = \dfrac{60}{7.5} = 8$.

**Answer:** $8$""",
                },
            ],
        },
        {
            "order": 4,
            "hint": r"""**Theorem 8:** any two sides of a triangle together are longer than the third. **Theorem 7:** the larger angle is opposite the longer side.""",
            "parts": [
                {
                    "label": "(a)",
                    "prompt": r"""A triangle has sides of length $7$, $11$ and $x$, where $x$ is a whole number.

Find the **smallest** possible value of $x$.""",
                    "answer": "5",
                    "expected_format": WHOLE,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** By **Theorem 8**, $x + 7 > 11$, so $x > 4$.

**Step 2:** The smallest whole number greater than $4$ is $5$.

*Check:* $x = 4$ fails, because $4 + 7 = 11$ gives a flat "triangle".

**Answer:** $5$""",
                },
                {
                    "label": "(b)",
                    "prompt": r"""Find the **largest** possible value of $x$.""",
                    "answer": "17",
                    "expected_format": WHOLE,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** By **Theorem 8**, $7 + 11 > x$, so $x < 18$.

**Step 2:** The largest whole number less than $18$ is $17$.

**Answer:** $17$""",
                },
                {
                    "label": "(c)",
                    "prompt": r"""In a different triangle $PQR$, $|\angle QPR| = 50^\circ$ and $|\angle PQR| = 70^\circ$. Its three sides measure $8.0$, $9.0$ and $9.8$ cm, in some order.

Without measuring or using trigonometry, find $|PQ|$.""",
                    "answer": "9",
                    "expected_format": LENGTH,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** The third angle is $|\angle PRQ| = 180 - 50 - 70 = 60^\circ$ (**Theorem 4**).

**Step 2:** By **Theorem 7**, a larger angle has a longer side opposite it. Order the angles: $50^\circ < 60^\circ < 70^\circ$. So the sides opposite them are, in order, $8.0 < 9.0 < 9.8$.

**Step 3:** $[PQ]$ is opposite the angle at $R$, which is $60^\circ$, the middle angle. So $|PQ| = 9.0$.

**Answer:** $9$ cm""",
                },
            ],
        },
    ]),
]


class Command(BaseCommand):
    help = "Add or update the Geometry-Theorems practice questions"

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
            missing = []
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
                            "solution": None,
                            "is_copyrighted": True,
                            "is_exam_question": False,
                            "is_quickkick_suitable": False,
                        },
                    )
                    questions += 1
                    self.stdout.write(
                        f'    {"created" if made else "updated"} question {question.order}'
                    )

                    for order, part in enumerate(entry["parts"]):
                        extra = {}
                        image = part.get("image")
                        if image:
                            if (Path(settings.MEDIA_ROOT) / image).exists():
                                extra["image"] = image
                            else:
                                missing.append(image)
                        QuestionPart.objects.update_or_create(
                            question=question,
                            label=part["label"],
                            defaults={
                                **extra,
                                "prompt": part["prompt"],
                                "answer": part["answer"],
                                "expected_format": part["expected_format"],
                                "solution": part["solution"],
                                "expected_type": part["expected_type"],
                                "max_marks": part["max_marks"],
                                "order": order,
                                "solution_unlock_after_attempts": 2,
                                "scale": None,
                                "is_quickkick_suitable": False,
                            },
                        )
                        parts += 1

            if dry_run:
                transaction.set_rollback(True)

        for image in missing:
            self.stderr.write(self.style.WARNING(
                f"  not attached, no file at MEDIA_ROOT/{image} - copy it and re-run"
            ))

        prefix = "Would touch" if dry_run else "Wrote"
        self.stdout.write(self.style.SUCCESS(
            f"\n{prefix} {questions} questions and {parts} parts."
        ))
