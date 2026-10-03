"""Draw the diagrams for the Congruence & Proof practice questions.

Writes PNGs to media/question_part_images/cp_*.png; the
add_congruence_proof_questions command attaches each to its question's part (a).
media/ is git-ignored, so this script is the source of truth: re-run it to
rebuild them. Drawing helpers are shared with geometry_theorem_diagrams.py.

Same rules as there: every figure is placed from the question's own numbers, so
it is to scale, and only what the question states is labelled.

    python scripts/congruence_proof_diagrams.py
"""
import numpy as np
from matplotlib.patches import Polygon

from geometry_theorem_diagrams import (
    FS, P, polar, seg, poly, point_label, angle_mark, right_angle, tick,
    parallel_arrow, length_label, frame, new_axes, save,
)


def name_points(ax, pts, names, centre, dist=0.32):
    for p, n in zip(pts, names):
        point_label(ax, p, n, centre, dist=dist)


def foot(p, a, b):
    d = (b - a) / np.linalg.norm(b - a)
    return a + np.dot(p - a, d) * d


def warmup1_kite():
    """Kite ABCD: |AB| = |AD|, |CB| = |CD|; angle ABC = 110, angle BAD = 50."""
    a = P(0, 0)
    # angle BAC = 25, angle BCA = 45, so angle ABC = 110; scale |AC| = 4
    ac = 4.0
    ab = ac * np.sin(np.radians(45)) / np.sin(np.radians(110))
    b = polar(ab, 25)
    d = polar(ab, -25)
    c = P(ac, 0)
    fig, ax = new_axes(6, 3.6)
    poly(ax, a, b, c, d)
    seg(ax, a, c, lw=1.2, ls=(0, (5, 4)))
    tick(ax, a, b)
    tick(ax, a, d)
    tick(ax, c, b, n=2)
    tick(ax, c, d, n=2)
    angle_mark(ax, b, a, c, r"$110^\circ$", r=0.35, text_r=0.8)
    name_points(ax, (a, b, c, d), "ABCD", P(ac / 2, 0))
    frame(ax, [a, b, c, d], pad=0.6)
    save(fig, "cp_warmup1_kite.png")


def warmup2_ratio():
    """XY parallel to BC; |AX| = 4, |XB| = 6, |XY| = 5."""
    a, b, c = P(1.4, 4.4), P(0, 0), P(5.0, 0)
    x = a + 0.4 * (b - a)
    y = a + 0.4 * (c - a)
    fig, ax = new_axes(5.5, 5)
    poly(ax, a, b, c)
    seg(ax, x, y)
    parallel_arrow(ax, x, y)
    parallel_arrow(ax, b, c)
    centre = (a + b + c) / 3
    length_label(ax, a, x, "4", centre)
    length_label(ax, x, b, "6", centre)
    length_label(ax, x, y, "5", c, dist=0.25)
    name_points(ax, (a, b, c), "ABC", centre)
    point_label(ax, x, "X", y)
    point_label(ax, y, "Y", x)
    frame(ax, [a, b, c], pad=0.5)
    save(fig, "cp_warmup2_ratio.png")


def warmup3_three_parallels():
    """Three parallel lines; |AB| = |BC| = 5 on one transversal; 3x-1, x+7 on the other."""
    ys = (3.0, 1.5, 0)
    fig, ax = new_axes(6.5, 4)
    for y in ys:
        seg(ax, P(-0.8, y), P(5.6, y))
        parallel_arrow(ax, P(-0.8, y), P(5.6, y), at=0.93)
    left = [P(0.4 + 0.3 * k, y) for k, y in enumerate(ys)]
    right = [P(2.6 + 1.0 * k, y) for k, y in enumerate(ys)]
    seg(ax, left[0] + P(-0.1, 0.5), left[2] + P(0.1, -0.5))
    seg(ax, right[0] + P(-0.33, 0.5), right[2] + P(0.33, -0.5))
    mid = (left[1] + right[1]) / 2
    length_label(ax, left[0], left[1], "5", mid, dist=0.35)
    length_label(ax, left[1], left[2], "5", mid, dist=0.35)
    length_label(ax, right[0], right[1], r"$3x-1$", mid, dist=0.6)
    length_label(ax, right[1], right[2], r"$x+7$", mid, dist=0.55)
    for p, n in zip(left, "ABC"):
        ax.text(*(p + P(0.32, 0.22)), n, fontsize=FS + 1, style="italic", ha="center")
    for p, n in zip(right, "DEF"):
        ax.text(*(p + P(0.35, 0.22)), n, fontsize=FS + 1, style="italic", ha="center")
    frame(ax, [P(-0.8, -0.6), P(5.6, 3.6)], pad=0.3)
    save(fig, "cp_warmup3_three_parallels.png")


def warmup4_similar():
    """ABC similar to DEF; |AB| 6, |BC| 8, |AC| 7; |DE| 9."""
    s = 0.32
    b, c = P(0, 0), P(8 * s, 0)
    ang_b = np.degrees(np.arccos((6 ** 2 + 8 ** 2 - 7 ** 2) / (2 * 6 * 8)))
    a = b + 6 * s * polar(1, ang_b)
    k, shift = 1.5, P(3.8, 0)
    d, e, f = shift + k * a, shift + k * b, shift + k * c
    fig, ax = new_axes(7, 3.6)
    poly(ax, a, b, c)
    poly(ax, d, e, f)
    for v, p, q, n in ((b, c, a, 1), (e, f, d, 1), (c, a, b, 2), (f, d, e, 2)):
        for i in range(n):
            angle_mark(ax, v, p, q, "", r=0.28 + 0.07 * i)
    cen1, cen2 = (a + b + c) / 3, (d + e + f) / 3
    length_label(ax, a, b, "6", cen1)
    length_label(ax, b, c, "8", cen1)
    length_label(ax, a, c, "7", cen1)
    length_label(ax, d, e, "9", cen2)
    name_points(ax, (a, b, c), "ABC", cen1)
    name_points(ax, (d, e, f), "DEF", cen2)
    frame(ax, [a, b, c, d, e, f], pad=0.6)
    save(fig, "cp_warmup4_similar.png")


def workout1_isosceles_altitude():
    """|AB| = |AC| = 13, |BC| = 10, AD perpendicular to BC."""
    s = 0.3
    b, c = P(0, 0), P(10 * s, 0)
    a = P(5 * s, 12 * s)
    d = P(5 * s, 0)
    fig, ax = new_axes(4, 5)
    poly(ax, a, b, c)
    seg(ax, a, d)
    right_angle(ax, d, c, a, s=0.22)
    centre = (a + b + c) / 3
    length_label(ax, a, b, "13", centre, dist=0.35)
    length_label(ax, a, c, "13", centre, dist=0.35)
    name_points(ax, (a, b, c), "ABC", centre)
    ax.text(*(d + P(0, -0.35)), "D", fontsize=FS + 1, ha="center", style="italic")
    frame(ax, [a, b, c], pad=0.6)
    save(fig, "cp_workout1_isosceles_altitude.png")


def workout2_ratio_23():
    """XY parallel to BC with |AX| : |XB| = 2 : 3; |AC| = 20, |XY| = 6."""
    a, b, c = P(2.0, 4.6), P(0, 0), P(5.6, 0)
    x = a + 0.4 * (b - a)
    y = a + 0.4 * (c - a)
    fig, ax = new_axes(5.5, 5)
    poly(ax, a, b, c)
    seg(ax, x, y)
    parallel_arrow(ax, x, y)
    parallel_arrow(ax, b, c)
    centre = (a + b + c) / 3
    length_label(ax, x, y, "6", c, dist=0.25)
    name_points(ax, (a, b, c), "ABC", centre)
    point_label(ax, x, "X", y)
    point_label(ax, y, "Y", x)
    frame(ax, [a, b, c], pad=0.5)
    save(fig, "cp_workout2_ratio_23.png")


def workout3_crossed_similar():
    """D on [AB], E on [AC], angle ADE = angle ACB; |AD| 4, |AE| 5, |AC| 8, |DE| 3.

    Drawn to scale: |AB| 10, |AC| 8, |BC| 6 has its right angle at C, and
    |AD| 4, |AE| 5, |DE| 3 has its right angle at D.
    """
    s = 0.48
    a = P(0, 0)
    ang_a = np.degrees(np.arctan2(6, 8))  # angle BAC
    c = 8 * s * polar(1, 0)
    b = 10 * s * polar(1, ang_a)
    d = 4 * s * polar(1, ang_a)
    e = 5 * s * polar(1, 0)
    fig, ax = new_axes(6, 4.4)
    poly(ax, a, b, c)
    seg(ax, d, e)
    angle_mark(ax, d, a, e, "", r=0.3)
    angle_mark(ax, c, b, a, "", r=0.3)
    centre = (a + b + c) / 3
    length_label(ax, a, d, "4", c)
    length_label(ax, a, e, "5", b)
    length_label(ax, d, e, "3", a, dist=0.28)
    name_points(ax, (a, b, c), "ABC", centre)
    point_label(ax, d, "D", c)
    ax.text(*(e + P(0, -0.38)), "E", fontsize=FS + 1, ha="center", style="italic")
    frame(ax, [a, b, c], pad=0.6)
    save(fig, "cp_workout3_crossed_similar.png")


def workout4_square():
    """Square ABCD of side 10; E the midpoint of [BC], F the midpoint of [CD]."""
    s = 0.36
    a, b, c, d = P(0, 0), P(10 * s, 0), P(10 * s, 10 * s), P(0, 10 * s)
    e, f = (b + c) / 2, (c + d) / 2
    fig, ax = new_axes(4.6, 4.6)
    poly(ax, a, b, c, d)
    seg(ax, a, e)
    seg(ax, b, f)
    tick(ax, b, e)
    tick(ax, e, c)
    tick(ax, c, f, n=2)
    tick(ax, f, d, n=2)
    length_label(ax, a, b, "10", c, dist=0.32)
    centre = (a + c) / 2
    name_points(ax, (a, b, c, d), "ABCD", centre)
    ax.text(*(e + P(0.35, 0)), "E", fontsize=FS + 1, va="center", style="italic")
    ax.text(*(f + P(0, 0.35)), "F", fontsize=FS + 1, ha="center", style="italic")
    frame(ax, [a, b, c, d], pad=0.6)
    save(fig, "cp_workout4_square.png")


def stretch1_two_parallels():
    """XY parallel to BC, YZ parallel to AB; |AX| 3, |XB| 5, |BC| 16."""
    s = 0.34
    b, c = P(0, 0), P(16 * s, 0)
    a = P(4.5 * s, 11 * s)
    x = a + (3 / 8) * (b - a)
    y = a + (3 / 8) * (c - a)
    z = b + (y - x)  # XBZY is a parallelogram
    fig, ax = new_axes(6, 4.6)
    poly(ax, a, b, c)
    seg(ax, x, y)
    seg(ax, y, z)
    parallel_arrow(ax, x, y)
    parallel_arrow(ax, b, c, at=0.75)
    parallel_arrow(ax, x, b, n=2, at=0.78)
    parallel_arrow(ax, y, z, n=2, at=0.55)
    centre = (a + b + c) / 3
    length_label(ax, a, x, "3", centre)
    length_label(ax, x, b, "5", centre)
    name_points(ax, (a, b, c), "ABC", centre)
    point_label(ax, x, "X", y)
    point_label(ax, y, "Y", x)
    ax.text(*(z + P(0, -0.38)), "Z", fontsize=FS + 1, ha="center", style="italic")
    frame(ax, [a, b, c], pad=0.6)
    save(fig, "cp_stretch1_two_parallels.png")


def stretch2_altitude():
    """Right angle at C; CD perpendicular to AB; |AD| 4, |DB| 9."""
    s = 0.42
    a, b = P(0, 0), P(13 * s, 0)
    d = P(4 * s, 0)
    c = P(4 * s, 6 * s)
    fig, ax = new_axes(6.4, 3.6)
    poly(ax, a, b, c)
    seg(ax, c, d)
    right_angle(ax, c, a, b, s=0.25)
    right_angle(ax, d, b, c, s=0.22)
    length_label(ax, a, d, "4", c, dist=0.32)
    length_label(ax, d, b, "9", c, dist=0.32)
    name_points(ax, (a, b, c), "ABC", (a + b + c) / 3)
    ax.text(*(d + P(0, -0.38)), "D", fontsize=FS + 1, ha="center", style="italic")
    frame(ax, [a, b, c], pad=0.6)
    save(fig, "cp_stretch2_altitude.png")


def stretch3_shadow():
    """Student 1.6 m, 2.4 m from the shadow tip; tree 9.6 m further on."""
    s = 0.45
    tip = P(0, 0)
    st = P(2.4 * s, 0)
    tr = P(12 * s, 0)
    head = st + P(0, 1.6 * s)
    top = tr + P(0, 8 * s)
    fig, ax = new_axes(7, 4.4)
    seg(ax, tip + P(-0.3, 0), tr + P(0.6, 0))
    seg(ax, st, head, lw=3)
    seg(ax, tr, top, lw=4)
    seg(ax, tip, top, lw=1.1, ls=(0, (5, 4)))
    right_angle(ax, st, tr, head, s=0.15)
    right_angle(ax, tr, tip, top, s=0.2)
    ax.text(*(head + P(-0.15, 0.25)), "1.6 m", fontsize=FS - 2, ha="right")
    length_label(ax, tip, st, "2.4 m", top, dist=0.35)
    length_label(ax, st, tr, "9.6 m", top, dist=0.35)
    ax.text(*(top + P(0.25, -0.6)), "tree", fontsize=FS - 1, ha="left")
    frame(ax, [tip, tr, top], pad=0.6)
    save(fig, "cp_stretch3_shadow.png")


def stretch4_area():
    """XY parallel to BC; |AX| 4, |AB| 12, |BC| 18; area of ABC 81."""
    s = 0.3
    b, c = P(0, 0), P(18 * s, 0)
    a = P(6 * s, 9 * s)
    x = a + (1 / 3) * (b - a)
    y = a + (1 / 3) * (c - a)
    fig, ax = new_axes(6, 4.2)
    ax.add_patch(Polygon([x, b, c, y], closed=True, facecolor="#e6e6e6", edgecolor="none"))
    poly(ax, a, b, c)
    seg(ax, x, y)
    parallel_arrow(ax, x, y)
    parallel_arrow(ax, b, c)
    centre = (a + b + c) / 3
    length_label(ax, a, x, "4", centre)
    length_label(ax, b, c, "18", a, dist=0.32)
    name_points(ax, (a, b, c), "ABC", centre)
    point_label(ax, x, "X", y)
    point_label(ax, y, "Y", x)
    frame(ax, [a, b, c], pad=0.6)
    save(fig, "cp_stretch4_area.png")


if __name__ == "__main__":
    warmup1_kite()
    warmup2_ratio()
    warmup3_three_parallels()
    warmup4_similar()
    workout1_isosceles_altitude()
    workout2_ratio_23()
    workout3_crossed_similar()
    workout4_square()
    stretch1_two_parallels()
    stretch2_altitude()
    stretch3_shadow()
    stretch4_area()
