"""Add the Constructions practice questions: four Warm-up, four Workout, four Stretch.

Content authored on local and replayed here so production gets exactly what was
tested. Idempotent: keyed on topic slug, section name and question order rather
than primary key, because ids differ between local and production. Re-running
updates in place and never duplicates.

Covers the Leaving Cert constructions 16-22: circumcentre and circumcircle,
incentre and incircle, the 60 degree angle, the tangent at a point, the
parallelogram from its sides and angle, the centroid and the orthocentre.
A construction itself cannot be typed, so each question marks a number that
follows from it, and part (a) asks the student to construct it on paper and
photograph it ("Photograph my working") for feedback. Where it helps, the
prompt gives a measurement to check the drawing against.

Twelve part (a)s carry a diagram from scripts/constructions_diagrams.py showing
only the figure given; copy media/question_part_images/con_*.png to production
before running this there.
"""
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Subject
from interactive_lessons.models import Topic, Question, QuestionPart, Section

TOPIC_SLUG = "geometry-constructions"
TOPIC_NAME = "Constructions"
SUBJECT_NAME = "Maths"
PAPER = "p2"
TOPIC_ORDER = 18

DEGREES = "Number of degrees (e.g., 72)"
DEGREES_1DP = "Degrees, correct to one decimal place (e.g., 41.4)"
LENGTH = "Number only (e.g., 7.5)"
SURD = r"Exact surd or decimal to 2 places (e.g., $3\sqrt{5}$ or 6.71)"
PI_FORMAT = r"In terms of $\pi$, number only (e.g., $48\pi$)"
SLOPE = "A number or fraction (e.g., -2 or 3/4)"

PHOTO = r"""

✏️ **Construct it:** {task} Then tap **📷 Photograph my working** for feedback on your construction."""


def construct(prompt, task):
    return prompt + PHOTO.format(task=task)


# (section name, section order, [questions])
QUESTIONS = [
    ("""Warm-up""", 1, [
        {
            "order": 1,
            "hint": r"""The **centroid** is where the three medians meet (construction 21). It divides each median in the ratio $2 : 1$, measured from the vertex.""",
            "parts": [
                {
                    "label": "(a)",
                    "image": "question_part_images/con_warmup1_centroid.png",
                    "prompt": construct(r"""$G$ is the centroid of the triangle $ABC$, and $D$ is the midpoint of $[BC]$. The median $[AD]$ has length $12$.

Find $|AG|$.""", r"""draw any triangle, bisect two of its sides (construction 2) and join each midpoint to the opposite vertex. Where the medians cross is the centroid."""),
                    "answer": "8",
                    "expected_format": LENGTH,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** The centroid divides each median in the ratio $2 : 1$ from the vertex, so $|AG|$ is $\dfrac{2}{3}$ of $|AD|$.

**Step 2:** $|AG| = \dfrac{2}{3} \times 12 = 8$.

**Answer:** $8$""",
                },
                {
                    "label": "(b)",
                    "prompt": r"""Given also that $|BG| = 10$, find the length of the median from $B$.""",
                    "answer": "15",
                    "expected_format": LENGTH,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** $[BG]$ is the $2$ part of that median's $2 : 1$ split, which is $\dfrac{2}{3}$ of the whole median.

**Step 2:** Median $= 10 \times \dfrac{3}{2} = 15$.

**Answer:** $15$""",
                },
            ],
        },
        {
            "order": 2,
            "hint": r"""The **circumcentre** is where the perpendicular bisectors of the sides meet (construction 16). In a right-angled triangle it lands on the hypotenuse: by the corollary of Theorem 19, the hypotenuse is a diameter.""",
            "parts": [
                {
                    "label": "(a)",
                    "image": "question_part_images/con_warmup2_right_triangle.png",
                    "prompt": construct(r"""The triangle $ABC$ has a right angle at $B$, with $|AB| = 6$ cm and $|BC| = 8$ cm.

Find the radius of its circumcircle, in cm.""", r"""draw the triangle full size, construct the perpendicular bisectors of two sides, and draw the circumcircle. Its radius should measure $5$ cm, and its centre should sit on $[AC]$."""),
                    "answer": "5",
                    "expected_format": LENGTH,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** The angle at $B$ is $90^\circ$, so $[AC]$ is a diameter of the circumcircle (an angle in a semicircle is a right angle, the corollary of Theorem 19). The circumcentre is the midpoint of $[AC]$.

**Step 2:** $|AC| = \sqrt{6^2 + 8^2} = 10$ (**Theorem 14**).

**Step 3:** Radius $= \dfrac{10}{2} = 5$ cm.

**Answer:** $5$ cm""",
                },
                {
                    "label": "(b)",
                    "prompt": r"""Find the area of the circumcircle, in terms of $\pi$.""",
                    "answer": "25*pi",
                    "expected_format": PI_FORMAT,
                    "expected_type": "expression",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** Area $= \pi r^2 = \pi (5)^2$.

**Answer:** $25\pi$ cm²""",
                },
            ],
        },
        {
            "order": 3,
            "hint": r"""In the $60^\circ$ construction (construction 18), both arcs have the **same radius** as $|AB|$, so all three sides of the triangle $ABC$ are equal.""",
            "parts": [
                {
                    "label": "(a)",
                    "image": "question_part_images/con_warmup3_sixty.png",
                    "prompt": construct(r"""To construct an angle of $60^\circ$ at $A$, mark $B$ on the ray with $|AB| = 5$ cm. Then draw an arc centred at $A$ and an arc centred at $B$, each with radius $5$ cm. They meet at $C$.

Find $|BC|$, in cm.""", r"""construct the $60^\circ$ angle with only a compass and straight edge, then bisect it (construction 1). Check both angles with a protractor afterwards."""),
                    "answer": "5",
                    "expected_format": LENGTH,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** $C$ is on the arc centred at $B$ with radius $5$ cm, so $|BC| = 5$ cm.

**Why it works:** $|AC| = 5$ too (the arc centred at $A$), so $ABC$ is equilateral. All its angles are equal and add to $180^\circ$ (**Theorem 4**), so $|\angle CAB| = 60^\circ$.

**Answer:** $5$ cm""",
                },
                {
                    "label": "(b)",
                    "prompt": r"""The angle $\angle CAB$ is then bisected. What size is each of the two new angles?""",
                    "answer": "30",
                    "expected_format": DEGREES,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** Bisecting halves the angle: $\dfrac{60}{2} = 30$.

*Note:* this is how $30^\circ$ (and, bisecting again, $15^\circ$) is made without a protractor.

**Answer:** $30^\circ$""",
                },
            ],
        },
        {
            "order": 4,
            "hint": r"""The tangent at $P$ is **perpendicular to the radius** $[OP]$ (Theorem 20). That is why construction 19 draws the line through $P$ perpendicular to $OP$.""",
            "parts": [
                {
                    "label": "(a)",
                    "image": "question_part_images/con_warmup4_tangent.png",
                    "prompt": construct(r"""A circle has centre $O$ and radius $5$. The tangent at the point $P$ on the circle passes through $Q$, with $|PQ| = 12$.

Find $|OQ|$.""", r"""draw a circle, mark a point $P$ on it, draw the line $OP$ beyond $P$, and construct the line through $P$ perpendicular to it (construction 4). That line is the tangent."""),
                    "answer": "13",
                    "expected_format": LENGTH,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** The tangent is perpendicular to the radius at $P$ (**Theorem 20**), so the triangle $OPQ$ has a right angle at $P$.

**Step 2:** By **Theorem 14**, $|OQ| = \sqrt{5^2 + 12^2} = \sqrt{169} = 13$.

**Answer:** $13$""",
                },
                {
                    "label": "(b)",
                    "prompt": r"""Find $|\angle OQP|$, correct to one decimal place.""",
                    "answer": "22.6199",
                    "expected_format": DEGREES_1DP,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** In the right-angled triangle $OPQ$, $[OP]$ is opposite $\angle OQP$ and $[PQ]$ is adjacent to it:

$$\tan \angle OQP = \frac{5}{12}$$

**Step 2:** $|\angle OQP| = \tan^{-1}\left(\dfrac{5}{12}\right) = 22.6^\circ$.

**Answer:** $22.6^\circ$""",
                },
            ],
        },
    ]),
    ("""Workout""", 2, [
        {
            "order": 1,
            "hint": r"""The **incentre** is where the angle bisectors meet (construction 17), and it is the same distance $r$ from all three sides. Joining it to the vertices splits the triangle into three triangles, each of height $r$.""",
            "parts": [
                {
                    "label": "(a)",
                    "image": "question_part_images/con_workout1_incircle.png",
                    "prompt": construct(r"""The triangle $ABC$ has $|AB| = 13$, $|BC| = 14$ and $|CA| = 15$. The perpendicular height from $A$ to $BC$ is $12$.

Find the area of the triangle.""", r"""draw a half-size copy, with sides $6.5$ cm, $7$ cm and $7.5$ cm. Bisect two of its angles (construction 1) to find the incentre, then draw the incircle. Its radius should measure $2$ cm."""),
                    "answer": "84",
                    "expected_format": LENGTH,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** Area $= \dfrac{1}{2} \times$ base $\times$ height $= \dfrac{1}{2} \times 14 \times 12$.

**Step 2:** Area $= 84$.

**Answer:** $84$""",
                },
                {
                    "label": "(b)",
                    "prompt": r"""Find the radius of the incircle.""",
                    "answer": "4",
                    "expected_format": LENGTH,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** Join the incentre $I$ to $A$, $B$ and $C$. This makes three triangles with bases $13$, $14$ and $15$, each of height $r$, because the incentre is the same distance from every side.

**Step 2:** Their areas add up to the whole:

$$\frac{1}{2}r(13 + 14 + 15) = 84 \quad\Rightarrow\quad 21r = 84 \quad\Rightarrow\quad r = 4$$

**Answer:** $4$ (so $2$ cm on the half-size drawing)""",
                },
            ],
        },
        {
            "order": 2,
            "hint": r"""Every point on the perpendicular bisector of a segment is the same distance from both ends. The circumcentre lies on two of them, so it is the same distance from all three vertices.""",
            "parts": [
                {
                    "label": "(a)",
                    "image": "question_part_images/con_workout2_circumcentre.png",
                    "prompt": construct(r"""The triangle has vertices $A(-4, 0)$, $B(4, 0)$ and $C(0, 8)$. Its circumcentre is the point $(0, k)$.

Find $k$.""", r"""plot the triangle on graph paper and construct the perpendicular bisectors of $[AB]$ and $[BC]$ (construction 2). They should cross at $(0, 3)$."""),
                    "answer": "3",
                    "expected_format": LENGTH,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** The perpendicular bisector of $[AB]$ is the $y$-axis, $x = 0$, because $A$ and $B$ are mirror images in it. So the circumcentre is $(0, k)$.

**Step 2:** The circumcentre is the same distance from $A$ as from $C$:

$$(0 + 4)^2 + (k - 0)^2 = (0 - 0)^2 + (k - 8)^2$$

$$16 + k^2 = k^2 - 16k + 64 \quad\Rightarrow\quad 16k = 48 \quad\Rightarrow\quad k = 3$$

**Answer:** $k = 3$""",
                },
                {
                    "label": "(b)",
                    "prompt": r"""Find the radius of the circumcircle.""",
                    "answer": "5",
                    "expected_format": LENGTH,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** Radius $=$ distance from $(0, 3)$ to $A(-4, 0)$:

$$\sqrt{4^2 + 3^2} = 5$$

**Check:** to $C(0, 8)$, the distance is $8 - 3 = 5$ ✓

**Answer:** $5$""",
                },
            ],
        },
        {
            "order": 3,
            "hint": r"""A **median** joins a vertex to the midpoint of the opposite side. The centroid $G$ is two-thirds of the way along each median from the vertex.""",
            "parts": [
                {
                    "label": "(a)",
                    "image": "question_part_images/con_workout3_centroid_coords.png",
                    "prompt": construct(r"""The triangle has vertices $A(0, 0)$, $B(10, 2)$ and $C(2, 10)$. $M$ is the midpoint of $[BC]$.

Find the length of the median $[AM]$.""", r"""plot the triangle on graph paper and construct two medians (construction 21). Their crossing point, the centroid, should be at $(4, 4)$."""),
                    "answer": "6*sqrt(2)",
                    "expected_format": SURD,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** $M = \left(\dfrac{10 + 2}{2}, \dfrac{2 + 10}{2}\right) = (6, 6)$.

**Step 2:** $|AM| = \sqrt{6^2 + 6^2} = \sqrt{72} = 6\sqrt{2} \approx 8.49$.

**Answer:** $6\sqrt{2}$""",
                },
                {
                    "label": "(b)",
                    "prompt": r"""$G$ is the centroid of the triangle. Find $|AG|$.""",
                    "answer": "4*sqrt(2)",
                    "expected_format": SURD,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Method 1:** $|AG| = \dfrac{2}{3}|AM| = \dfrac{2}{3} \times 6\sqrt{2} = 4\sqrt{2}$.

**Method 2:** $G = \left(\dfrac{0 + 10 + 2}{3}, \dfrac{0 + 2 + 10}{3}\right) = (4, 4)$, so $|AG| = \sqrt{4^2 + 4^2} = 4\sqrt{2} \approx 5.66$.

**Answer:** $4\sqrt{2}$""",
                },
            ],
        },
        {
            "order": 4,
            "hint": r"""An **altitude** goes from a vertex perpendicular to the opposite side. The orthocentre is where the altitudes meet (construction 22). Perpendicular slopes multiply to $-1$.""",
            "parts": [
                {
                    "label": "(a)",
                    "image": "question_part_images/con_workout4_orthocentre.png",
                    "prompt": construct(r"""The triangle has vertices $A(0, 0)$, $B(6, 0)$ and $C(2, 4)$.

Find the slope of the altitude from $A$.""", r"""plot the triangle on graph paper and construct the perpendiculars from $A$ to $BC$ and from $C$ to $AB$ (construction 3). They should cross at $(2, 2)$."""),
                    "answer": "1",
                    "expected_format": SLOPE,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** Slope of $BC = \dfrac{4 - 0}{2 - 6} = -1$.

**Step 2:** The altitude from $A$ is perpendicular to $BC$, so its slope is $1$, since $(-1)(1) = -1$.

**Answer:** $1$""",
                },
                {
                    "label": "(b)",
                    "prompt": r"""The orthocentre is $(2, k)$. Find $k$.""",
                    "answer": "2",
                    "expected_format": LENGTH,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** The altitude from $C$ is perpendicular to $AB$, which lies on the $x$-axis, so it is the vertical line $x = 2$.

**Step 2:** The altitude from $A$ is $y = x$ (slope $1$, through the origin).

**Step 3:** They meet where $x = 2$ and $y = 2$, so $k = 2$.

**Answer:** $k = 2$""",
                },
            ],
        },
    ]),
    ("""Stretch""", 3, [
        {
            "order": 1,
            "hint": r"""Area of a parallelogram $= ab\sin C$, using two neighbouring sides and the angle between them. Neighbouring angles in a parallelogram add to $180^\circ$, which helps with the diagonal.""",
            "parts": [
                {
                    "label": "(a)",
                    "image": "question_part_images/con_stretch1_parallelogram.png",
                    "prompt": construct(r"""The parallelogram $ABCD$ has $|AB| = 8$ cm, $|AD| = 5$ cm and $|\angle DAB| = 60^\circ$.

Find its area, in cm².""", r"""construct the parallelogram (construction 20), making the $60^\circ$ angle without a protractor (construction 18). Then measure the diagonal $[AC]$: it should be about $11.4$ cm."""),
                    "answer": "20*sqrt(3)",
                    "expected_format": SURD,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** Area $= |AB| \times |AD| \times \sin 60^\circ = 8 \times 5 \times \dfrac{\sqrt{3}}{2}$.

**Step 2:** Area $= 20\sqrt{3} \approx 34.64$ cm².

**Answer:** $20\sqrt{3}$ cm²""",
                },
                {
                    "label": "(b)",
                    "prompt": r"""Find the length of the diagonal $[AC]$, in cm.""",
                    "answer": "sqrt(129)",
                    "expected_format": SURD,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** $|\angle ABC| = 180^\circ - 60^\circ = 120^\circ$ (neighbouring angles of a parallelogram), and $|BC| = |AD| = 5$ (**Theorem 9**).

**Step 2:** By the cosine rule in the triangle $ABC$:

$$|AC|^2 = 8^2 + 5^2 - 2(8)(5)\cos 120^\circ = 89 + 40 = 129$$

**Step 3:** $|AC| = \sqrt{129} \approx 11.36$ cm.

**Answer:** $\sqrt{129}$ cm""",
                },
            ],
        },
        {
            "order": 2,
            "hint": r"""First check whether the triangle is right-angled (**Theorem 15**). If it is, the circumcentre is the midpoint of the hypotenuse, and the inradius comes from splitting the area into three triangles at the incentre.""",
            "parts": [
                {
                    "label": "(a)",
                    "image": "question_part_images/con_stretch2_7_24_25.png",
                    "prompt": construct(r"""A triangle has sides $7$, $24$ and $25$.

Find the radius of its circumcircle.""", r"""draw a half-size copy, with sides $3.5$ cm, $12$ cm and $12.5$ cm, and construct both its circumcircle and its incircle (constructions 16 and 17). The radii should measure about $6.25$ cm and $1.5$ cm."""),
                    "answer": "12.5",
                    "expected_format": LENGTH,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** $7^2 + 24^2 = 49 + 576 = 625 = 25^2$, so the triangle is right-angled (**Theorem 15**), with hypotenuse $25$.

**Step 2:** The hypotenuse is a diameter of the circumcircle (angle in a semicircle), so the radius is $\dfrac{25}{2} = 12.5$.

**Answer:** $12.5$""",
                },
                {
                    "label": "(b)",
                    "prompt": r"""Find the radius of its incircle.""",
                    "answer": "3",
                    "expected_format": LENGTH,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** Area $= \dfrac{1}{2} \times 7 \times 24 = 84$ (the two shorter sides are perpendicular).

**Step 2:** Joining the incentre to the vertices splits the triangle into three triangles of height $r$:

$$\frac{1}{2}r(7 + 24 + 25) = 84 \quad\Rightarrow\quad 28r = 84 \quad\Rightarrow\quad r = 3$$

**Answer:** $3$""",
                },
            ],
        },
        {
            "order": 3,
            "hint": r"""In an **equilateral** triangle every median is also an altitude, a perpendicular bisector and an angle bisector. So the centroid, circumcentre, incentre and orthocentre are all the **same point**.""",
            "parts": [
                {
                    "label": "(a)",
                    "image": "question_part_images/con_stretch3_equilateral.png",
                    "prompt": construct(r"""$ABC$ is an equilateral triangle with sides of $6$ cm.

Find the radius of its circumcircle, in cm.""", r"""construct the triangle using the $60^\circ$ construction (18), then construct its circumcentre (16) and its centroid (21). They should land on the same point."""),
                    "answer": "2*sqrt(3)",
                    "expected_format": SURD,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** The height (a median) is $\sqrt{6^2 - 3^2} = \sqrt{27} = 3\sqrt{3}$ (**Theorem 14**).

**Step 2:** The circumcentre is the centroid, which is $\dfrac{2}{3}$ of the way down the median from the vertex. The radius is the distance to a vertex:

$$\frac{2}{3} \times 3\sqrt{3} = 2\sqrt{3} \approx 3.46 \text{ cm}$$

**Answer:** $2\sqrt{3}$ cm""",
                },
                {
                    "label": "(b)",
                    "prompt": r"""Find the radius of its incircle, in cm.""",
                    "answer": "sqrt(3)",
                    "expected_format": SURD,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** The incentre is the same point. Its distance to the base is the remaining $\dfrac{1}{3}$ of the median:

$$\frac{1}{3} \times 3\sqrt{3} = \sqrt{3} \approx 1.73 \text{ cm}$$

**Check:** circumradius $=$ $2 \times$ inradius, the $2 : 1$ split of the median ✓

**Answer:** $\sqrt{3}$ cm""",
                },
            ],
        },
        {
            "order": 4,
            "hint": r"""The tangent at $P$ is perpendicular to the radius $[CP]$ (Theorem 20), so its slope is the **negative reciprocal** of the slope of $CP$.""",
            "parts": [
                {
                    "label": "(a)",
                    "image": "question_part_images/con_stretch4_tangent_coords.png",
                    "prompt": construct(r"""A circle has centre $C(2, 1)$, and $P(6, 3)$ is a point on it.

Find the slope of the tangent to the circle at $P$.""", r"""draw the circle on graph paper (radius $\sqrt{20} \approx 4.5$ units), then construct the tangent at $P$ (construction 19). It should cross the $y$-axis at $(0, 15)$."""),
                    "answer": "-2",
                    "expected_format": SLOPE,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** Slope of the radius $CP = \dfrac{3 - 1}{6 - 2} = \dfrac{1}{2}$.

**Step 2:** The tangent is perpendicular to $CP$ (**Theorem 20**), so its slope is $-2$, since $\dfrac{1}{2} \times (-2) = -1$.

**Answer:** $-2$""",
                },
                {
                    "label": "(b)",
                    "prompt": r"""The tangent at $P$ crosses the $y$-axis at $(0, c)$. Find $c$.""",
                    "answer": "15",
                    "expected_format": LENGTH,
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** Equation of the tangent: $y - 3 = -2(x - 6)$, which is $y = -2x + 15$.

**Step 2:** At $x = 0$, $y = 15$.

**Answer:** $c = 15$""",
                },
            ],
        },
    ]),
]


class Command(BaseCommand):
    help = "Add or update the Constructions practice questions"

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
