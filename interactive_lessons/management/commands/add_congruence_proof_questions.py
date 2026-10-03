"""Add the Congruence & Proof practice questions: four Warm-up, four Workout, four Stretch.

Content authored on local and replayed here so production gets exactly what was
tested. Idempotent: keyed on topic slug, section name and question order rather
than primary key, because ids differ between local and production. Re-running
updates in place and never duplicates. Creates the topic on first run, placed
just after Angles, Lines & Triangles (slug geometry-theorems) on Paper 2.

This is Geometry II: congruent triangles (Axiom 4: SSS, SAS, ASA, RHS) and
Theorems 11-13, whose proofs are Higher Level only and live in the Proof Jigsaw
flashcards. Every answer is a number; each solution names the congruence case
or theorem behind each step.

Twelve part (a)s carry a diagram from scripts/congruence_proof_diagrams.py.
Images live in media/, which git does not carry, so copy
media/question_part_images/cp_*.png to production before running this there; a
missing file is reported and skipped rather than attached as a broken image.
"""
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Subject
from interactive_lessons.models import Topic, Question, QuestionPart, Section

TOPIC_SLUG = "congruence-proof"
TOPIC_NAME = "Congruence & Proof"
SUBJECT_NAME = "Maths"
PAPER = "p2"
TOPIC_ORDER = 18

DEGREES = "Number of degrees (e.g., 72)"
LENGTH = "Number only (e.g., 7.5)"
SURD = r"Exact surd or decimal to 2 places (e.g., $3\sqrt{5}$ or 6.71)"
WHOLE = "Whole number only (e.g., 9)"

# (section name, section order, [questions])
QUESTIONS = [
    ("""Warm-up""", 1, [
        {
            "order": 1,
            "hint": r"""Two triangles are **congruent** when one of SSS, SAS, ASA or RHS matches (Axiom 4). A side **shared** by both triangles counts as an equal pair.""",
            "parts": [
                {
                    "label": "(a)",
                    "image": "question_part_images/cp_warmup1_kite.png",
                    "prompt": r"""$ABCD$ is a kite with $|AB| = |AD|$ and $|CB| = |CD|$, and $|\angle ABC| = 110^\circ$.

Find $|\angle ADC|$.""",
                    "answer": "110",
                    "expected_format": DEGREES,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** Compare the triangles $ABC$ and $ADC$:
- $|AB| = |AD|$ (given)
- $|CB| = |CD|$ (given)
- $[AC]$ is common to both

**Step 2:** All three pairs of sides are equal, so the triangles are congruent by **SSS** (Axiom 4).

**Step 3:** Corresponding angles of congruent triangles are equal. $\angle ADC$ matches $\angle ABC$:

$$|\angle ADC| = 110^\circ$$

**Answer:** $110^\circ$""",
                },
                {
                    "label": "(b)",
                    "prompt": r"""Given also that $|\angle BAD| = 50^\circ$, find $|\angle BCD|$.""",
                    "answer": "90",
                    "expected_format": DEGREES,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** The angles in a quadrilateral add to $360^\circ$ (it splits into two triangles, **Theorem 4**).

**Step 2:**

$$|\angle BCD| = 360 - 110 - 110 - 50 = 90$$

**Answer:** $90^\circ$""",
                },
            ],
        },
        {
            "order": 2,
            "hint": r"""**Theorem 12:** a line parallel to one side of a triangle cuts the other two sides in the same ratio. To compare $XY$ with $BC$, use the **whole** side: the triangles $AXY$ and $ABC$ are similar (**Theorem 13**).""",
            "parts": [
                {
                    "label": "(a)",
                    "image": "question_part_images/cp_warmup2_ratio.png",
                    "prompt": r"""In the triangle $ABC$, $XY \parallel BC$ with $X$ on $[AB]$ and $Y$ on $[AC]$. $|AX| = 4$, $|XB| = 6$ and $|AC| = 15$.

Find $|AY|$.""",
                    "answer": "6",
                    "expected_format": LENGTH,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** By **Theorem 12**, $XY$ cuts $[AC]$ in the same ratio as $[AB]$: $|AY| : |YC| = 4 : 6$.

**Step 2:** So $[AY]$ is $\dfrac{4}{10}$ of the whole of $[AC]$:

$$|AY| = \frac{4}{10} \times 15 = 6$$

**Answer:** $6$""",
                },
                {
                    "label": "(b)",
                    "prompt": r"""Given that $|XY| = 5$, find $|BC|$.""",
                    "answer": "12.5",
                    "expected_format": LENGTH,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** The triangles $AXY$ and $ABC$ are similar: they share $\angle A$, and $XY \parallel BC$ gives equal corresponding angles.

**Step 2:** Their sides are proportional (**Theorem 13**), with the scale factor $\dfrac{|AB|}{|AX|} = \dfrac{10}{4} = 2.5$:

$$|BC| = 2.5 \times 5 = 12.5$$

**Answer:** $12.5$""",
                },
            ],
        },
        {
            "order": 3,
            "hint": r"""**Theorem 11:** if three parallel lines cut off equal segments on one transversal, they cut off equal segments on **every** transversal.""",
            "parts": [
                {
                    "label": "(a)",
                    "image": "question_part_images/cp_warmup3_three_parallels.png",
                    "prompt": r"""Three parallel lines cut one transversal at $A$, $B$, $C$ with $|AB| = |BC| = 5$, and a second transversal at $D$, $E$, $F$ with $|DE| = 3x - 1$ and $|EF| = x + 7$.

Find the value of $x$.""",
                    "answer": "4",
                    "expected_format": WHOLE,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** The lines cut equal segments on the first transversal, so by **Theorem 11** they cut equal segments on the second: $|DE| = |EF|$.

**Step 2:**

$$3x - 1 = x + 7 \quad\Rightarrow\quad 2x = 8 \quad\Rightarrow\quad x = 4$$

**Answer:** $x = 4$""",
                },
                {
                    "label": "(b)",
                    "prompt": r"""Find $|DF|$.""",
                    "answer": "22",
                    "expected_format": LENGTH,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** $|DE| = 3(4) - 1 = 11$ and $|EF| = 4 + 7 = 11$.

**Step 2:** $|DF| = 11 + 11 = 22$.

*Note:* the segments on the second transversal are equal to **each other**, not to the $5$s on the first.

**Answer:** $22$""",
                },
            ],
        },
        {
            "order": 4,
            "hint": r"""**Theorem 13:** similar triangles have their sides in proportion, **in order**. Match the sides using the equal angles, then find the scale factor from one known pair.""",
            "parts": [
                {
                    "label": "(a)",
                    "image": "question_part_images/cp_warmup4_similar.png",
                    "prompt": r"""The triangles $ABC$ and $DEF$ are similar, with $\angle B = \angle E$ and $\angle C = \angle F$. $|AB| = 6$, $|BC| = 8$, $|AC| = 7$ and $|DE| = 9$.

Find $|EF|$.""",
                    "answer": "12",
                    "expected_format": LENGTH,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** The matching is $A \leftrightarrow D$, $B \leftrightarrow E$, $C \leftrightarrow F$, so $[DE]$ matches $[AB]$ and $[EF]$ matches $[BC]$.

**Step 2:** Scale factor $= \dfrac{|DE|}{|AB|} = \dfrac{9}{6} = 1.5$.

**Step 3:** By **Theorem 13**, $|EF| = 1.5 \times 8 = 12$.

**Answer:** $12$""",
                },
                {
                    "label": "(b)",
                    "prompt": r"""Find $|DF|$.""",
                    "answer": "10.5",
                    "expected_format": LENGTH,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** $[DF]$ matches $[AC]$.

**Step 2:** $|DF| = 1.5 \times 7 = 10.5$.

**Answer:** $10.5$""",
                },
            ],
        },
    ]),
    ("""Workout""", 2, [
        {
            "order": 1,
            "hint": r"""**RHS:** two right-angled triangles are congruent if their hypotenuses are equal and one other pair of sides is equal. Then use Pythagoras (**Theorem 14**).""",
            "parts": [
                {
                    "label": "(a)",
                    "image": "question_part_images/cp_workout1_isosceles_altitude.png",
                    "prompt": r"""In the triangle $ABC$, $|AB| = |AC| = 13$ and $|BC| = 10$. $D$ is the point on $[BC]$ with $AD \perp BC$.

Find $|BD|$.""",
                    "answer": "5",
                    "expected_format": LENGTH,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** Compare the triangles $ABD$ and $ACD$:
- both have a right angle at $D$
- hypotenuses $|AB| = |AC| = 13$
- $[AD]$ is common to both

**Step 2:** They are congruent by **RHS** (Axiom 4), so $|BD| = |DC|$: $D$ is the midpoint of $[BC]$.

**Step 3:** $|BD| = \dfrac{10}{2} = 5$.

**Answer:** $5$""",
                },
                {
                    "label": "(b)",
                    "prompt": r"""Find $|AD|$.""",
                    "answer": "12",
                    "expected_format": LENGTH,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** The triangle $ABD$ is right-angled at $D$, with hypotenuse $[AB]$ (**Theorem 14**):

$$|AD|^2 = 13^2 - 5^2 = 169 - 25 = 144$$

**Step 2:** $|AD| = 12$.

**Answer:** $12$""",
                },
            ],
        },
        {
            "order": 2,
            "hint": r"""A ratio of $2 : 3$ splits a side into $2 + 3 = 5$ equal parts. **Theorem 12** carries the ratio across to the other side.""",
            "parts": [
                {
                    "label": "(a)",
                    "image": "question_part_images/cp_workout2_ratio_23.png",
                    "prompt": r"""In the triangle $ABC$, $XY \parallel BC$ with $X$ on $[AB]$ and $Y$ on $[AC]$. $|AX| : |XB| = 2 : 3$ and $|AC| = 20$.

Find $|AY|$.""",
                    "answer": "8",
                    "expected_format": LENGTH,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** By **Theorem 12**, $|AY| : |YC| = 2 : 3$ too.

**Step 2:** $[AC]$ splits into $5$ equal parts of $\dfrac{20}{5} = 4$, and $[AY]$ is $2$ of them:

$$|AY| = 2 \times 4 = 8$$

**Answer:** $8$""",
                },
                {
                    "label": "(b)",
                    "prompt": r"""Given that $|XY| = 6$, find $|BC|$.""",
                    "answer": "15",
                    "expected_format": LENGTH,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** The triangles $AXY$ and $ABC$ are similar, with $\dfrac{|AX|}{|AB|} = \dfrac{2}{5}$.

**Step 2:** By **Theorem 13**, $\dfrac{|XY|}{|BC|} = \dfrac{2}{5}$, so

$$|BC| = 6 \times \frac{5}{2} = 15$$

*Watch out:* $\dfrac{2}{3}$ is the ratio of the two **pieces** of $[AB]$. The triangles compare a piece with the **whole**, which is $\dfrac{2}{5}$.

**Answer:** $15$""",
                },
            ],
        },
        {
            "order": 3,
            "hint": r"""The triangles $ADE$ and $ACB$ are similar, but $DE$ is **not** parallel to $BC$. Match the vertices by their equal angles, not by where they sit in the diagram.""",
            "parts": [
                {
                    "label": "(a)",
                    "image": "question_part_images/cp_workout3_crossed_similar.png",
                    "prompt": r"""In the triangle $ABC$, $D$ is on $[AB]$ and $E$ is on $[AC]$, with $|\angle ADE| = |\angle ACB|$. $|AD| = 4$, $|AE| = 5$ and $|AC| = 8$.

Find $|AB|$.""",
                    "answer": "10",
                    "expected_format": LENGTH,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** The triangles $ADE$ and $ACB$ share $\angle A$, and $|\angle ADE| = |\angle ACB|$. So the third angles are equal too (**Theorem 4**), and the triangles are similar with

$$A \leftrightarrow A, \quad D \leftrightarrow C, \quad E \leftrightarrow B$$

**Step 2:** Match the sides in that order (**Theorem 13**): $[AD] \leftrightarrow [AC]$ and $[AE] \leftrightarrow [AB]$.

$$\frac{|AD|}{|AC|} = \frac{|AE|}{|AB|} \quad\Rightarrow\quad \frac{4}{8} = \frac{5}{|AB|} \quad\Rightarrow\quad |AB| = 10$$

*Watch out:* pairing $[AD]$ with $[AB]$ (as if $DE \parallel BC$) gives the wrong answer, $6.4$.

**Answer:** $10$""",
                },
                {
                    "label": "(b)",
                    "prompt": r"""Given that $|DE| = 3$, find $|BC|$.""",
                    "answer": "6",
                    "expected_format": LENGTH,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** $[DE]$ matches $[CB]$, and the scale factor from $ADE$ to $ACB$ is $\dfrac{|AC|}{|AD|} = \dfrac{8}{4} = 2$.

**Step 2:** $|BC| = 2 \times 3 = 6$.

**Answer:** $6$""",
                },
            ],
        },
        {
            "order": 4,
            "hint": r"""Look for two congruent right-angled triangles, $ABE$ and $BCF$. Equal angles in them will help with the angle between the lines.""",
            "parts": [
                {
                    "label": "(a)",
                    "image": "question_part_images/cp_workout4_square.png",
                    "prompt": r"""$ABCD$ is a square of side $10$. $E$ is the midpoint of $[BC]$ and $F$ is the midpoint of $[CD]$.

Find $|BF|$.""",
                    "answer": "5*sqrt(5)",
                    "expected_format": SURD,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** The triangle $BCF$ is right-angled at $C$, with $|BC| = 10$ and $|CF| = 5$.

**Step 2:** By **Theorem 14**:

$$|BF|^2 = 10^2 + 5^2 = 125 \quad\Rightarrow\quad |BF| = \sqrt{125} = 5\sqrt{5} \approx 11.18$$

*Also:* the triangle $ABE$ has the same two sides around its right angle, $|AB| = 10$ and $|BE| = 5$, so $ABE$ and $BCF$ are congruent (**SAS**) and $|AE| = |BF|$.

**Answer:** $5\sqrt{5}$""",
                },
                {
                    "label": "(b)",
                    "prompt": r"""Find the angle between the lines $AE$ and $BF$.""",
                    "answer": "90",
                    "expected_format": DEGREES,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** The triangles $ABE$ and $BCF$ are congruent (**SAS**), so $|\angle BAE| = |\angle CBF|$. Call this angle $\theta$.

**Step 2:** In the triangle $ABE$, $|\angle AEB| = 90^\circ - \theta$ (**Theorem 4**).

**Step 3:** Let $AE$ and $BF$ meet at $G$. In the triangle $BGE$, the angle at $B$ is $\theta$ and the angle at $E$ is $90^\circ - \theta$, so the angle at $G$ is

$$180 - \theta - (90 - \theta) = 90$$

**Answer:** $90^\circ$: the lines are perpendicular.""",
                },
            ],
        },
    ]),
    ("""Stretch""", 3, [
        {
            "order": 1,
            "hint": r"""Use **Theorem 12** twice, once for each parallel line. Then spot the parallelogram $XBZY$ (**Theorem 9**).""",
            "parts": [
                {
                    "label": "(a)",
                    "image": "question_part_images/cp_stretch1_two_parallels.png",
                    "prompt": r"""In the triangle $ABC$, $X$ is on $[AB]$ and $Y$ is on $[AC]$ with $XY \parallel BC$. $Z$ is on $[BC]$ with $YZ \parallel AB$. $|AX| = 3$, $|XB| = 5$ and $|BC| = 16$.

Find $|BZ|$.""",
                    "answer": "6",
                    "expected_format": LENGTH,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** $XY \parallel BC$, so by **Theorem 12**, $|AY| : |YC| = 3 : 5$.

**Step 2:** $YZ \parallel AB$ in the triangle $CAB$. By **Theorem 12** again, $Z$ cuts $[CB]$ in the same ratio as $Y$ cuts $[CA]$: $|CZ| : |ZB| = 5 : 3$.

**Step 3:** $|BZ| = \dfrac{3}{8} \times 16 = 6$.

**Answer:** $6$""",
                },
                {
                    "label": "(b)",
                    "prompt": r"""Find $|XY|$.""",
                    "answer": "6",
                    "expected_format": LENGTH,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** $XY \parallel BZ$ and $YZ \parallel XB$, so $XBZY$ is a parallelogram.

**Step 2:** Opposite sides of a parallelogram are equal (**Theorem 9**): $|XY| = |BZ| = 6$.

**Check (Theorem 13):** $\dfrac{|XY|}{|BC|} = \dfrac{|AX|}{|AB|} = \dfrac{3}{8}$, so $|XY| = \dfrac{3}{8} \times 16 = 6$ ✓

**Answer:** $6$""",
                },
            ],
        },
        {
            "order": 2,
            "hint": r"""The perpendicular from the right angle makes **three** similar triangles: $ABC$, $ACD$ and $CBD$. This is the figure from the proof of Pythagoras.""",
            "parts": [
                {
                    "label": "(a)",
                    "image": "question_part_images/cp_stretch2_altitude.png",
                    "prompt": r"""The triangle $ABC$ has a right angle at $C$. $D$ is on $[AB]$ with $CD \perp AB$. $|AD| = 4$ and $|DB| = 9$.

Find $|CD|$.""",
                    "answer": "6",
                    "expected_format": LENGTH,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** The triangles $ACD$ and $CBD$ are similar. Each has a right angle at $D$, and $|\angle ACD| = 90^\circ - |\angle BCD| = |\angle CBD|$. So $A \leftrightarrow C$, $C \leftrightarrow B$, $D \leftrightarrow D$.

**Step 2:** By **Theorem 13**:

$$\frac{|AD|}{|CD|} = \frac{|CD|}{|DB|} \quad\Rightarrow\quad |CD|^2 = 4 \times 9 = 36$$

**Step 3:** $|CD| = 6$.

**Answer:** $6$""",
                },
                {
                    "label": "(b)",
                    "prompt": r"""Find $|AC|$.""",
                    "answer": "2*sqrt(13)",
                    "expected_format": SURD,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Method 1 (Pythagoras):** The triangle $ACD$ is right-angled at $D$:

$$|AC|^2 = 4^2 + 6^2 = 52$$

**Method 2 (similar triangles, as in the proof of Theorem 14):** $|AC|^2 = |AB| \cdot |AD| = 13 \times 4 = 52$.

**So** $|AC| = \sqrt{52} = 2\sqrt{13} \approx 7.21$.

**Answer:** $2\sqrt{13}$""",
                },
            ],
        },
        {
            "order": 3,
            "hint": r"""The sun's rays are parallel, so the student and the tree, standing upright, make two similar right-angled triangles that share the angle at the shadow's tip.""",
            "parts": [
                {
                    "label": "(a)",
                    "image": "question_part_images/cp_stretch3_shadow.png",
                    "prompt": r"""A student $1.6$ m tall stands so that the tip of her shadow is at the same point as the tip of a tree's shadow. She is $2.4$ m from that point and $9.6$ m from the tree.

Find the height of the tree, in metres.""",
                    "answer": "8",
                    "expected_format": LENGTH,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** The two triangles share the angle at the tip and both have a right angle at the ground, so they are similar.

**Step 2:** The tree is $2.4 + 9.6 = 12$ m from the tip. The scale factor is $\dfrac{12}{2.4} = 5$.

**Step 3:** By **Theorem 13**, the tree's height is $5 \times 1.6 = 8$ m.

*Watch out:* using $9.6$ instead of $12$ is the usual slip. Both distances must be measured from the **same** point, the tip.

**Answer:** $8$ m""",
                },
                {
                    "label": "(b)",
                    "prompt": r"""At the same time, a $2$ m pole is placed upright so its shadow also ends at the same point. How far from the tree is the pole, in metres?""",
                    "answer": "9",
                    "expected_format": LENGTH,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** Every upright object here has height $: $ distance from the tip $= 1.6 : 2.4 = 2 : 3$.

**Step 2:** The pole is $\dfrac{3}{2} \times 2 = 3$ m from the tip.

**Step 3:** The tree is $12$ m from the tip, so the pole is $12 - 3 = 9$ m from the tree.

**Answer:** $9$ m""",
                },
            ],
        },
        {
            "order": 4,
            "hint": r"""When similar shapes have lengths in the ratio $1 : k$, their **areas** are in the ratio $1 : k^2$.""",
            "parts": [
                {
                    "label": "(a)",
                    "image": "question_part_images/cp_stretch4_area.png",
                    "prompt": r"""In the triangle $ABC$, $XY \parallel BC$, with $|AX| = 4$, $|AB| = 12$ and $|BC| = 18$.

Find $|XY|$.""",
                    "answer": "6",
                    "expected_format": LENGTH,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** The triangles $AXY$ and $ABC$ are similar ($XY \parallel BC$), with scale factor $\dfrac{|AX|}{|AB|} = \dfrac{4}{12} = \dfrac{1}{3}$.

**Step 2:** By **Theorem 13**, $|XY| = \dfrac{1}{3} \times 18 = 6$.

**Answer:** $6$""",
                },
                {
                    "label": "(b)",
                    "prompt": r"""The area of the triangle $ABC$ is $81$. Find the area of the shaded region $XBCY$.""",
                    "answer": "72",
                    "expected_format": LENGTH,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** The lengths are in the ratio $1 : 3$, so the areas are in the ratio $1^2 : 3^2 = 1 : 9$.

**Step 2:** Area of $AXY = \dfrac{81}{9} = 9$.

**Step 3:** Area of $XBCY = 81 - 9 = 72$.

*Watch out:* the area is **not** $\dfrac{1}{3}$ of $81$. Both the base and the height shrink by $\dfrac{1}{3}$.

**Answer:** $72$""",
                },
            ],
        },
    ]),
]


class Command(BaseCommand):
    help = "Add or update the Congruence & Proof practice questions"

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
                defaults={"name": TOPIC_NAME, "subject": subject, "paper": PAPER,
                          "order": TOPIC_ORDER},
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
