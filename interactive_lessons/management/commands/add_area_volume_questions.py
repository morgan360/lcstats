"""Add the Area & Volume practice questions: three Easy, three Medium, three Hard.

Content authored on local and replayed here so production gets exactly what was
tested. Idempotent: keyed on topic slug, section name and question order rather
than primary key, because ids differ between local and production. Re-running
updates in place and never duplicates.

Every formula used is printed in the Formulae & Tables booklet (pp. 8-12):
cylinder, cone, sphere, frustum, prism and the trapezoidal rule. The questions
test choosing and combining them, not recalling them.

Answers in terms of pi are stored as ``k*pi`` with k a whole number, because
that is the form the grader parses both numerically (so a decimal such as
904.78 is accepted) and algebraically (so ``288\\pi`` is accepted). A
fractional multiple such as ``256*pi/3`` defeats the algebraic check and falls
through to GPT, so the numbers here are chosen to avoid one.

No Markdown tables: Tailwind's reset strips their borders and padding on the
question page, so the cells run together ("1015", "1.01.2x"). Readings are
set out as a display-maths list instead.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Subject
from interactive_lessons.models import Topic, Question, QuestionPart, Section

TOPIC_SLUG = "area-volume"
TOPIC_NAME = "Area & Volume"
SUBJECT_NAME = "Maths"
PAPER = "p2"

PI_FORMAT = r"""In terms of $\pi$, number only (e.g., $48\pi$)"""

# (section name, section order, [questions])
QUESTIONS = [
    ("""Easy""", 1, [
        {
            "order": 1,
            "hint": r"""The sphere and cylinder formulae are on page 10 of the *Formulae & Tables*. When a solid is **melted down and recast**, the volume stays the same: set the two volume expressions equal and solve.""",
            "parts": [
                {
                    "label": "(a)",
                    "prompt": r"""A solid metal sphere has a radius of $6$ cm.

Find the volume of the sphere, in terms of $\pi$.""",
                    "answer": "288*pi",
                    "expected_format": PI_FORMAT,
                    "expected_type": "expression",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** Use the volume of a sphere (*Formulae & Tables*, p. 10):

$$V = \frac{4}{3}\pi r^3$$

**Step 2:** Substitute $r = 6$:

$$V = \frac{4}{3}\pi(6)^3 = \frac{4}{3}\pi(216) = 288\pi$$

**Answer:** $288\pi$ cm³""",
                },
                {
                    "label": "(b)",
                    "prompt": r"""Find the surface area of the sphere, in terms of $\pi$.""",
                    "answer": "144*pi",
                    "expected_format": PI_FORMAT,
                    "expected_type": "expression",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** Use the surface area of a sphere:

$$A = 4\pi r^2$$

**Step 2:** Substitute $r = 6$:

$$A = 4\pi(6)^2 = 4\pi(36) = 144\pi$$

**Answer:** $144\pi$ cm²""",
                },
                {
                    "label": "(c)",
                    "prompt": r"""The sphere is melted down and all of the metal is recast into a solid cylinder of radius $6$ cm.

Find the height of the cylinder.""",
                    "answer": "8",
                    "expected_format": "Number only, in cm (e.g., 12)",
                    "expected_type": "numeric",
                    "max_marks": 10,
                    "solution": r"""**Step 1:** Melting and recasting keeps the volume the same:

$$\text{Volume of cylinder} = \text{Volume of sphere}$$

**Step 2:** Write the cylinder's volume with $r = 6$:

$$\pi r^2 h = \pi(6)^2 h = 36\pi h$$

**Step 3:** Set equal to the sphere's volume from part (a) and solve:

$$36\pi h = 288\pi$$

$$h = \frac{288}{36} = 8$$

**Answer:** $8$ cm""",
                },
            ],
        },
        {
            "order": 2,
            "hint": r"""For a cone, the radius $r$, the perpendicular height $h$ and the slant height $l$ form a right-angled triangle, so $l^2 = r^2 + h^2$. The curved surface area uses the **slant** height; the volume uses the **perpendicular** height.""",
            "parts": [
                {
                    "label": "(a)",
                    "prompt": r"""A solid cone has a base radius of $5$ cm and a perpendicular height of $12$ cm.

Find the slant height of the cone.""",
                    "answer": "13",
                    "expected_format": "Number only, in cm (e.g., 10)",
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** The radius, perpendicular height and slant height form a right-angled triangle, with the slant height $l$ as the hypotenuse.

**Step 2:** Apply Pythagoras' theorem:

$$l^2 = r^2 + h^2 = 5^2 + 12^2 = 25 + 144 = 169$$

$$l = \sqrt{169} = 13$$

**Answer:** $13$ cm""",
                },
                {
                    "label": "(b)",
                    "prompt": r"""Find the curved surface area of the cone, in terms of $\pi$.""",
                    "answer": "65*pi",
                    "expected_format": PI_FORMAT,
                    "expected_type": "expression",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** Use the curved surface area of a cone (*Formulae & Tables*, p. 10):

$$A = \pi r l$$

**Step 2:** Substitute $r = 5$ and $l = 13$ from part (a):

$$A = \pi(5)(13) = 65\pi$$

**Answer:** $65\pi$ cm²""",
                },
                {
                    "label": "(c)",
                    "prompt": r"""Find the volume of the cone, in terms of $\pi$.""",
                    "answer": "100*pi",
                    "expected_format": PI_FORMAT,
                    "expected_type": "expression",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** Use the volume of a cone:

$$V = \frac{1}{3}\pi r^2 h$$

**Step 2:** Substitute $r = 5$ and the **perpendicular** height $h = 12$ (not the slant height):

$$V = \frac{1}{3}\pi(5)^2(12) = \frac{1}{3}\pi(25)(12) = 100\pi$$

**Answer:** $100\pi$ cm³""",
                },
            ],
        },
        {
            "order": 3,
            "hint": r"""The trapezoidal rule is on page 12 of the *Formulae & Tables*: $A \approx \frac{h}{2}\left[y_1 + y_n + 2(y_2 + y_3 + \dots + y_{n-1})\right]$. Here $h$ is the **gap between offsets**, not an offset. The first and last offsets are counted once; every other offset is doubled.""",
            "parts": [
                {
                    "label": "(a)",
                    "prompt": r"""A surveyor measures the width of an irregular field along a straight boundary. Offsets are taken at intervals of $10$ m, and are, in order:

$$12 \text{ m}, \quad 18 \text{ m}, \quad 21 \text{ m}, \quad 24 \text{ m}, \quad 19 \text{ m}, \quad 15 \text{ m}, \quad 10 \text{ m}$$

Use the trapezoidal rule to estimate the area of the field.""",
                    "answer": "1080",
                    "expected_format": "Number only, in m² (e.g., 950)",
                    "expected_type": "numeric",
                    "max_marks": 10,
                    "solution": r"""**Step 1:** Identify the values. The interval is $h = 10$. The first and last offsets are $y_1 = 12$ and $y_7 = 10$; the middle offsets are $18, 21, 24, 19, 15$.

**Step 2:** Apply the trapezoidal rule:

$$A \approx \frac{h}{2}\left[y_1 + y_7 + 2(y_2 + y_3 + y_4 + y_5 + y_6)\right]$$

$$A \approx \frac{10}{2}\left[12 + 10 + 2(18 + 21 + 24 + 19 + 15)\right]$$

**Step 3:** Simplify:

$$A \approx 5\left[22 + 2(97)\right] = 5\left[22 + 194\right] = 5(216) = 1080$$

**Answer:** $1080$ m²""",
                },
                {
                    "label": "(b)",
                    "prompt": r"""The actual area of the field is $1100$ m².

Find the percentage error in the estimate from part (a), correct to two decimal places.""",
                    "answer": "1.82",
                    "expected_format": "Number only, correct to 2 decimal places, without the % sign (e.g., 2.35)",
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** Find the error:

$$\text{Error} = 1100 - 1080 = 20 \text{ m}^2$$

**Step 2:** Express it as a percentage of the **true** value:

$$\text{Percentage error} = \frac{\text{Error}}{\text{True value}} \times 100 = \frac{20}{1100} \times 100 = 1.8181\ldots\%$$

**Step 3:** Round to two decimal places.

**Answer:** $1.82\%$""",
                },
            ],
        },
    ]),
    ("""Medium""", 2, [
        {
            "order": 1,
            "hint": r"""Split the solid into the shapes it is made from and work on each separately. For the **surface area**, count only the faces you could actually touch: where the hemisphere sits on the cylinder, neither the top of the cylinder nor the flat face of the hemisphere is on the outside.""",
            "parts": [
                {
                    "label": "(a)",
                    "prompt": r"""A solid metal ornament is made from a cylinder with a hemisphere on top. The cylinder has radius $3$ cm and height $10$ cm. The hemisphere has the same radius as the cylinder.

Find the total volume of the ornament, in terms of $\pi$.""",
                    "answer": "108*pi",
                    "expected_format": PI_FORMAT,
                    "expected_type": "expression",
                    "max_marks": 10,
                    "solution": r"""**Step 1:** Volume of the cylinder:

$$V_{\text{cyl}} = \pi r^2 h = \pi(3)^2(10) = 90\pi$$

**Step 2:** Volume of the hemisphere, which is half a sphere:

$$V_{\text{hemi}} = \frac{1}{2} \times \frac{4}{3}\pi r^3 = \frac{2}{3}\pi(3)^3 = \frac{2}{3}\pi(27) = 18\pi$$

**Step 3:** Add:

$$V = 90\pi + 18\pi = 108\pi$$

**Answer:** $108\pi$ cm³""",
                },
                {
                    "label": "(b)",
                    "prompt": r"""Find the total surface area of the ornament, in terms of $\pi$. Include the flat circular base.""",
                    "answer": "87*pi",
                    "expected_format": PI_FORMAT,
                    "expected_type": "expression",
                    "max_marks": 10,
                    "solution": r"""**Step 1:** List the outside surfaces. The ornament has a flat circular base, the curved side of the cylinder and the curved surface of the hemisphere. The top of the cylinder is covered by the hemisphere, so it is not counted.

**Step 2:** Flat circular base:

$$\pi r^2 = \pi(3)^2 = 9\pi$$

**Step 3:** Curved surface of the cylinder:

$$2\pi r h = 2\pi(3)(10) = 60\pi$$

**Step 4:** Curved surface of the hemisphere, which is half of a sphere's surface area:

$$\frac{1}{2} \times 4\pi r^2 = 2\pi(3)^2 = 18\pi$$

**Step 5:** Add:

$$A = 9\pi + 60\pi + 18\pi = 87\pi$$

**Answer:** $87\pi$ cm²""",
                },
                {
                    "label": "(c)",
                    "prompt": r"""The ornament is melted down and recast into small solid spheres, each of radius $1.5$ cm. No metal is lost.

How many spheres can be made?""",
                    "answer": "24",
                    "expected_format": "Whole number (e.g., 15)",
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** Volume of one small sphere:

$$V = \frac{4}{3}\pi(1.5)^3 = \frac{4}{3}\pi(3.375) = 4.5\pi$$

**Step 2:** Divide the total volume from part (a) by the volume of one sphere:

$$\frac{108\pi}{4.5\pi} = 24$$

**Answer:** $24$ spheres""",
                },
            ],
        },
        {
            "order": 2,
            "hint": r"""When solid objects are dropped into water and are fully submerged, the **rise** in the water is a cylinder whose volume equals the total volume of the objects. The volume of water itself never changes, whatever container it is poured into.""",
            "parts": [
                {
                    "label": "(a)",
                    "prompt": r"""A cylindrical container has an internal radius of $8$ cm. It contains water to a depth of $15$ cm.

Find the volume of water in the container, in terms of $\pi$.""",
                    "answer": "960*pi",
                    "expected_format": PI_FORMAT,
                    "expected_type": "expression",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** The water forms a cylinder of radius $8$ cm and height $15$ cm.

**Step 2:**

$$V = \pi r^2 h = \pi(8)^2(15) = \pi(64)(15) = 960\pi$$

**Answer:** $960\pi$ cm³""",
                },
                {
                    "label": "(b)",
                    "prompt": r"""Identical solid steel balls, each of radius $2$ cm, are dropped into the container and sink to the bottom. They are all fully covered by the water.

How many balls are needed to raise the water level by exactly $4$ cm?""",
                    "answer": "24",
                    "expected_format": "Whole number (e.g., 18)",
                    "expected_type": "numeric",
                    "max_marks": 10,
                    "solution": r"""**Step 1:** The rise in the water is a cylinder of radius $8$ cm and height $4$ cm. Its volume equals the total volume of the balls:

$$V_{\text{rise}} = \pi(8)^2(4) = 256\pi$$

**Step 2:** Volume of one ball:

$$V_{\text{ball}} = \frac{4}{3}\pi(2)^3 = \frac{32}{3}\pi$$

**Step 3:** Number of balls:

$$n = \frac{256\pi}{\frac{32}{3}\pi} = 256 \times \frac{3}{32} = 24$$

**Answer:** $24$ balls""",
                },
                {
                    "label": "(c)",
                    "prompt": r"""The balls are removed. All of the water is then poured into an empty rectangular tank whose base measures $20$ cm by $16$ cm.

Find the depth of the water in the tank, correct to two decimal places.""",
                    "answer": "9.42",
                    "expected_format": "Number only, in cm, correct to 2 decimal places (e.g., 7.85)",
                    "expected_type": "numeric",
                    "max_marks": 10,
                    "solution": r"""**Step 1:** Removing the balls leaves the original $960\pi$ cm³ of water, from part (a).

**Step 2:** The water in the tank is a rectangular block (a prism) with base area $20 \times 16 = 320$ cm². Using $V = Bh$:

$$320 \times d = 960\pi$$

$$d = \frac{960\pi}{320} = 3\pi = 9.4247\ldots$$

**Step 3:** Round to two decimal places.

**Answer:** $9.42$ cm""",
                },
            ],
        },
        {
            "order": 3,
            "hint": r"""When a sector is folded into a cone, the **radius of the sector becomes the slant height** of the cone, and the **arc length of the sector becomes the circumference of the base**. Use $l = 2\pi r \cdot \frac{\theta}{360°}$ for the arc length when $\theta$ is in degrees.""",
            "parts": [
                {
                    "label": "(a)",
                    "prompt": r"""A sector of a circle has radius $15$ cm and angle $216°$. The two straight edges of the sector are joined, without overlap, to form the curved surface of a cone.

Find the arc length of the sector, in terms of $\pi$.""",
                    "answer": "18*pi",
                    "expected_format": PI_FORMAT,
                    "expected_type": "expression",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** Use the arc length formula for $\theta$ in degrees (*Formulae & Tables*, p. 9):

$$l = 2\pi r \cdot \frac{\theta}{360°}$$

**Step 2:** Substitute $r = 15$ and $\theta = 216°$:

$$l = 2\pi(15) \cdot \frac{216}{360} = 30\pi \times 0.6 = 18\pi$$

**Answer:** $18\pi$ cm""",
                },
                {
                    "label": "(b)",
                    "prompt": r"""Find the radius of the base of the cone.""",
                    "answer": "9",
                    "expected_format": "Number only, in cm (e.g., 6)",
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** The arc of the sector becomes the circumference of the cone's base:

$$2\pi r = 18\pi$$

**Step 2:** Solve:

$$r = \frac{18\pi}{2\pi} = 9$$

**Answer:** $9$ cm""",
                },
                {
                    "label": "(c)",
                    "prompt": r"""Find the perpendicular height of the cone.""",
                    "answer": "12",
                    "expected_format": "Number only, in cm (e.g., 8)",
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** The radius of the sector, $15$ cm, becomes the slant height $l$ of the cone.

**Step 2:** Apply Pythagoras' theorem with $l = 15$ and $r = 9$:

$$h^2 = l^2 - r^2 = 15^2 - 9^2 = 225 - 81 = 144$$

$$h = 12$$

**Answer:** $12$ cm""",
                },
                {
                    "label": "(d)",
                    "prompt": r"""Find the volume of the cone, in terms of $\pi$.""",
                    "answer": "324*pi",
                    "expected_format": PI_FORMAT,
                    "expected_type": "expression",
                    "max_marks": 10,
                    "solution": r"""**Step 1:** Use $V = \frac{1}{3}\pi r^2 h$ with $r = 9$ and $h = 12$:

$$V = \frac{1}{3}\pi(9)^2(12) = \frac{1}{3}\pi(81)(12) = 324\pi$$

**Answer:** $324\pi$ cm³""",
                },
            ],
        },
    ]),
    ("""Hard""", 3, [
        {
            "order": 1,
            "hint": r"""A frustum is a cone with its top cut off, and its formulae are on page 11 of the *Formulae & Tables*. To find the height of the **full** cone, use similar triangles: the radius grows in proportion to the distance from the tip. Water standing in the bucket forms a smaller frustum, which you can also find as the difference of two cones.""",
            "parts": [
                {
                    "label": "(a)",
                    "prompt": r"""A bucket is in the shape of a frustum of a cone. The radius of the open top is $15$ cm, the radius of the base is $10$ cm, and the perpendicular height is $12$ cm.

Find the capacity of the bucket, in terms of $\pi$.""",
                    "answer": "1900*pi",
                    "expected_format": PI_FORMAT,
                    "expected_type": "expression",
                    "max_marks": 10,
                    "solution": r"""**Step 1:** Use the volume of a frustum (*Formulae & Tables*, p. 11):

$$V = \frac{1}{3}\pi h\left(R^2 + Rr + r^2\right)$$

**Step 2:** Substitute $R = 15$, $r = 10$, $h = 12$:

$$V = \frac{1}{3}\pi(12)\left(15^2 + 15(10) + 10^2\right) = 4\pi\left(225 + 150 + 100\right) = 4\pi(475) = 1900\pi$$

**Answer:** $1900\pi$ cm³""",
                },
                {
                    "label": "(b)",
                    "prompt": r"""Find the area of the curved outer surface of the bucket, in terms of $\pi$. Do not include the base.""",
                    "answer": "325*pi",
                    "expected_format": PI_FORMAT,
                    "expected_type": "expression",
                    "max_marks": 10,
                    "solution": r"""**Step 1:** Find the slant height. Moving from the base edge to the top edge, the radius increases by $15 - 10 = 5$ cm over a height of $12$ cm. These form a right-angled triangle with the slant height $l$:

$$l = \sqrt{12^2 + 5^2} = \sqrt{169} = 13$$

**Step 2:** Use the curved surface area of a frustum:

$$A = \pi(r + R)l = \pi(10 + 15)(13) = 325\pi$$

**Answer:** $325\pi$ cm²""",
                },
                {
                    "label": "(c)",
                    "prompt": r"""The bucket can be thought of as a large cone with a small cone removed from its tip.

Find the perpendicular height of the large cone.""",
                    "answer": "36",
                    "expected_format": "Number only, in cm (e.g., 30)",
                    "expected_type": "numeric",
                    "max_marks": 10,
                    "solution": r"""**Step 1:** Let $x$ be the height of the small cone that was removed. Its base is the bucket's base, radius $10$. The large cone has height $x + 12$ and radius $15$.

**Step 2:** The two cones are similar, so radius is proportional to height:

$$\frac{10}{x} = \frac{15}{x + 12}$$

**Step 3:** Cross-multiply and solve:

$$10(x + 12) = 15x$$

$$10x + 120 = 15x$$

$$x = 24$$

**Step 4:** The large cone's height is $x + 12 = 36$.

**Answer:** $36$ cm""",
                },
                {
                    "label": "(d)",
                    "prompt": r"""The bucket stands on its base and water is poured in to a depth of $6$ cm.

What percentage of the bucket's capacity is filled? Give your answer correct to the nearest whole number.""",
                    "answer": "40",
                    "expected_format": "Whole number, without the % sign (e.g., 35)",
                    "expected_type": "numeric",
                    "max_marks": 10,
                    "solution": r"""**Step 1:** Find the radius at the water surface. The radius grows by $5$ cm over the full $12$ cm height, so over $6$ cm it grows by $\frac{6}{12} \times 5 = 2.5$ cm:

$$r_{\text{surface}} = 10 + 2.5 = 12.5$$

**Step 2:** The water is a frustum with $R = 12.5$, $r = 10$, $h = 6$:

$$V = \frac{1}{3}\pi(6)\left(12.5^2 + 12.5(10) + 10^2\right) = 2\pi\left(156.25 + 125 + 100\right) = 2\pi(381.25) = 762.5\pi$$

*(Check with the cones from part (c): a cone of height $30$, radius $12.5$, minus a cone of height $24$, radius $10$, gives $\frac{1}{3}\pi(156.25 \times 30 - 100 \times 24) = 762.5\pi$.)*

**Step 3:** Express as a percentage of the capacity from part (a):

$$\frac{762.5\pi}{1900\pi} \times 100 = 40.13\ldots\%$$

**Step 4:** Round to the nearest whole number. Note that although the water is **half** the bucket's depth, it fills **less than half** the bucket, because the bucket is narrower at the bottom.

**Answer:** $40\%$""",
                },
            ],
        },
        {
            "order": 2,
            "hint": r"""Write each volume in terms of $r$ before you substitute any numbers: the cone's height is given as a multiple of $r$, so the whole solid's volume becomes a single expression in $r$. For the surface area, the flat circular face where the cone meets the hemisphere is **inside** the solid and does not count.""",
            "parts": [
                {
                    "label": "(a)",
                    "prompt": r"""A solid toy is made from a hemisphere of radius $r$ cm with a cone of the same radius on its flat face. The perpendicular height of the cone is $2r$ cm.

Show that the volume of the toy is $\frac{4}{3}\pi r^3$ cm³.""",
                    "answer": r"""$\frac{2}{3}\pi r^3 + \frac{1}{3}\pi r^2(2r) = \frac{2}{3}\pi r^3 + \frac{2}{3}\pi r^3 = \frac{4}{3}\pi r^3$""",
                    "expected_format": r"""A short derivation: write the volume of each part in terms of $r$, then add them to reach $\frac{4}{3}\pi r^3$.""",
                    "expected_type": "manual",
                    "max_marks": 10,
                    "solution": r"""**Step 1:** Volume of the hemisphere, half of a sphere:

$$V_{\text{hemi}} = \frac{1}{2} \times \frac{4}{3}\pi r^3 = \frac{2}{3}\pi r^3$$

**Step 2:** Volume of the cone, with height $2r$:

$$V_{\text{cone}} = \frac{1}{3}\pi r^2(2r) = \frac{2}{3}\pi r^3$$

**Step 3:** Add:

$$V = \frac{2}{3}\pi r^3 + \frac{2}{3}\pi r^3 = \frac{4}{3}\pi r^3 \qquad \checkmark$$

*(The toy has the same volume as a full sphere of radius $r$.)*""",
                },
                {
                    "label": "(b)",
                    "prompt": r"""The volume of the toy is $36\pi$ cm³.

Find the value of $r$.""",
                    "answer": "3",
                    "expected_format": "Number only, in cm (e.g., 5)",
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** Use the result from part (a):

$$\frac{4}{3}\pi r^3 = 36\pi$$

**Step 2:** Divide both sides by $\pi$ and multiply by $\frac{3}{4}$:

$$r^3 = 36 \times \frac{3}{4} = 27$$

**Step 3:**

$$r = \sqrt[3]{27} = 3$$

**Answer:** $r = 3$ cm""",
                },
                {
                    "label": "(c)",
                    "prompt": r"""Find the total surface area of the toy, correct to two decimal places.""",
                    "answer": "119.77",
                    "expected_format": "Number only, in cm², correct to 2 decimal places (e.g., 85.34)",
                    "expected_type": "numeric",
                    "max_marks": 10,
                    "solution": r"""**Step 1:** The outside of the toy is the curved surface of the hemisphere and the curved surface of the cone. The flat face where they join is inside the toy.

**Step 2:** Curved surface of the hemisphere, with $r = 3$:

$$\frac{1}{2} \times 4\pi r^2 = 2\pi(3)^2 = 18\pi$$

**Step 3:** Slant height of the cone, with $r = 3$ and $h = 2r = 6$:

$$l = \sqrt{3^2 + 6^2} = \sqrt{45} = 3\sqrt{5}$$

**Step 4:** Curved surface of the cone:

$$\pi r l = \pi(3)(3\sqrt{5}) = 9\sqrt{5}\,\pi$$

**Step 5:** Add and evaluate:

$$A = 18\pi + 9\sqrt{5}\,\pi = \pi\left(18 + 9\sqrt{5}\right) = 119.7713\ldots$$

**Answer:** $119.77$ cm²""",
                },
                {
                    "label": "(d)",
                    "prompt": r"""The toy is dropped into a cylinder of internal radius $6$ cm which contains some water. The toy sinks and is completely covered by the water.

Find the rise in the water level.""",
                    "answer": "1",
                    "expected_format": "Number only, in cm (e.g., 2)",
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** The rise in the water is a cylinder of radius $6$ cm whose volume equals the toy's volume, $36\pi$ cm³.

**Step 2:** Let the rise be $d$:

$$\pi(6)^2 d = 36\pi$$

$$36\pi d = 36\pi$$

$$d = 1$$

**Answer:** $1$ cm""",
                },
            ],
        },
        {
            "order": 3,
            "hint": r"""A pool whose depth varies only along its length is a **prism**: its volume is the area of the side cross-section times the width ($V = Bh$, *Formulae & Tables*, p. 11). Use the trapezoidal rule on the depth readings to get that cross-section, keeping $x$ as an unknown. Remember $1 \text{ m}^3 = 1000$ litres.""",
            "parts": [
                {
                    "label": "(a)",
                    "prompt": r"""A swimming pool is $25$ m long and $10$ m wide. Its depth varies along its length but not across its width. The depth is measured every $5$ m along the length, starting at the shallow end, at $0, 5, 10, 15, 20$ and $25$ m. The depths, in metres, are, in order:

$$1.0, \quad 1.2, \quad x, \quad 2.0, \quad 2.4, \quad 2.6$$

Use the trapezoidal rule to find an expression, in terms of $x$, for the area of the side cross-section of the pool.""",
                    "answer": "37 + 5*x",
                    "expected_format": r"""Expression in $x$ (e.g., $24 + 3x$)""",
                    "expected_type": "expression",
                    "max_marks": 10,
                    "solution": r"""**Step 1:** Identify the values. The interval is $h = 5$. The first and last depths are $1.0$ and $2.6$; the middle depths are $1.2$, $x$, $2.0$ and $2.4$.

**Step 2:** Apply the trapezoidal rule:

$$A \approx \frac{5}{2}\left[1.0 + 2.6 + 2(1.2 + x + 2.0 + 2.4)\right]$$

**Step 3:** Simplify inside the bracket:

$$A \approx 2.5\left[3.6 + 2(5.6 + x)\right] = 2.5\left[3.6 + 11.2 + 2x\right] = 2.5\left[14.8 + 2x\right]$$

$$A \approx 37 + 5x$$

**Answer:** $37 + 5x$ m²""",
                },
                {
                    "label": "(b)",
                    "prompt": r"""The volume of the pool is $450$ m³.

Find the value of $x$.""",
                    "answer": "1.6",
                    "expected_format": "Number only, in m (e.g., 1.4)",
                    "expected_type": "numeric",
                    "max_marks": 10,
                    "solution": r"""**Step 1:** The pool is a prism, so its volume is the cross-sectional area times the width:

$$V = (37 + 5x) \times 10$$

**Step 2:** Set equal to $450$:

$$10(37 + 5x) = 450$$

$$37 + 5x = 45$$

$$5x = 8$$

$$x = 1.6$$

*(Check: $1.6$ lies between the neighbouring depths $1.2$ and $2.0$, as it should for a pool that gets steadily deeper.)*

**Answer:** $x = 1.6$ m""",
                },
                {
                    "label": "(c)",
                    "prompt": r"""The empty pool is filled by a pump that delivers $30$ litres of water per second.

How many minutes does it take to fill the pool?""",
                    "answer": "250",
                    "expected_format": "Number only, in minutes (e.g., 180)",
                    "expected_type": "numeric",
                    "max_marks": 5,
                    "solution": r"""**Step 1:** Convert the volume to litres, using $1 \text{ m}^3 = 1000$ litres:

$$450 \text{ m}^3 = 450\,000 \text{ litres}$$

**Step 2:** Time in seconds:

$$\frac{450\,000}{30} = 15\,000 \text{ seconds}$$

**Step 3:** Convert to minutes:

$$\frac{15\,000}{60} = 250 \text{ minutes}$$

*(That is $4$ hours $10$ minutes.)*

**Answer:** $250$ minutes""",
                },
            ],
        },
    ]),
]


class Command(BaseCommand):
    help = "Add or update the Area & Volume practice questions"

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
                                "order": order,
                                "solution_unlock_after_attempts": 2,
                                "scale": None,
                                "is_quickkick_suitable": False,
                            },
                        )
                        parts += 1

            if dry_run:
                transaction.set_rollback(True)

        prefix = "Would touch" if dry_run else "Wrote"
        self.stdout.write(self.style.SUCCESS(
            f"\n{prefix} {questions} questions and {parts} parts."
        ))
