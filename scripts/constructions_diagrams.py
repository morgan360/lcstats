"""Draw the diagrams for the Constructions practice questions (constructions 16-22).

Writes PNGs to media/question_part_images/con_*.png; the
add_constructions_questions command attaches each to its question's part (a).
media/ is git-ignored, so this script is the source of truth.

Each diagram shows only the figure the question *gives*. The construction is
the student's job, so no circumcircle, incircle, median or altitude a part asks
for is drawn, and the 7-24-25 triangle carries no right-angle mark.

    python scripts/constructions_diagrams.py
"""
import numpy as np
from matplotlib.patches import Circle, FancyArrowPatch

from geometry_theorem_diagrams import (
    FS, LW, P, polar, seg, poly, dot, point_label, angle_mark, right_angle,
    length_label, frame, new_axes, save,
)


def names(ax, pts, letters, dist=0.32):
    centre = sum(pts) / len(pts)
    for p, n in zip(pts, letters):
        point_label(ax, p, n, centre, dist=dist)


def axes(ax, xmin, xmax, ymin, ymax, step=2):
    for a, b in ((P(xmin, 0), P(xmax, 0)), (P(0, ymin), P(0, ymax))):
        ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=14,
                                     color="#555555", lw=1.1, shrinkA=0, shrinkB=0))
    ax.text(xmax, -0.5, r"$x$", fontsize=FS, ha="right", va="top")
    ax.text(0.3, ymax, r"$y$", fontsize=FS, ha="left", va="top")
    for x in range(int(np.ceil(xmin)), int(xmax)):
        if x and x % step == 0:
            ax.plot([x, x], [-0.12, 0.12], color="#555555", lw=1)
            ax.text(x, -0.3, str(x), fontsize=FS - 5, ha="center", va="top", color="#555555")
    for y in range(int(np.ceil(ymin)), int(ymax)):
        if y and y % step == 0:
            ax.plot([-0.12, 0.12], [y, y], color="#555555", lw=1)
            ax.text(-0.3, y, str(y), fontsize=FS - 5, ha="right", va="center", color="#555555")


def coord_label(ax, p, text, dx, dy):
    dot(ax, p)
    ax.text(p[0] + dx, p[1] + dy, text, fontsize=FS - 1, ha="center", va="center")


def warmup1_centroid():
    """Medians meet at the centroid G; the median from A is drawn, G on it."""
    a, b, c = P(1.5, 4.2), P(0, 0), P(5.2, 0.4)
    d = (b + c) / 2
    g = (a + b + c) / 3
    fig, ax = new_axes(5, 4.4)
    poly(ax, a, b, c)
    seg(ax, a, d, lw=1.4)
    dot(ax, g)
    names(ax, [a, b, c], "ABC")
    ax.text(*(d + P(0.05, -0.38)), "D", fontsize=FS + 1, ha="center", style="italic")
    ax.text(*(g + P(0.32, 0.05)), "G", fontsize=FS + 1, ha="center", style="italic")
    frame(ax, [a, b, c], pad=0.6)
    save(fig, "con_warmup1_centroid.png")


def warmup2_right_triangle():
    s = 0.5
    a, b, c = P(0, 6 * s), P(0, 0), P(8 * s, 0)
    fig, ax = new_axes(5, 3.6)
    poly(ax, a, b, c)
    right_angle(ax, b, a, c, s=0.25)
    length_label(ax, a, b, "6 cm", c, dist=0.55)
    length_label(ax, b, c, "8 cm", a, dist=0.35)
    names(ax, [a, b, c], "ABC")
    frame(ax, [a, b, c], pad=0.8)
    save(fig, "con_warmup2_right_triangle.png")


def warmup3_sixty():
    """The 60 degree construction: arcs of radius |AB| centred at A and at B meet at C."""
    s = 0.7
    a, b = P(0, 0), P(5 * s, 0)
    c = polar(5 * s, 60)
    fig, ax = new_axes(5.5, 4)
    seg(ax, a, P(6.6 * s, 0))
    r = 5 * s
    for centre, a0, a1 in ((a, -8, 75), (b, 105, 188)):
        t = np.radians(np.linspace(a0, a1, 80))
        ax.plot(centre[0] + r * np.cos(t), centre[1] + r * np.sin(t), color="k", lw=1.1)
    seg(ax, a, c)
    dot(ax, a)
    dot(ax, b)
    dot(ax, c)
    ax.text(*(a + P(-0.3, -0.3)), "A", fontsize=FS + 1, style="italic", ha="center")
    ax.text(*(b + P(0.15, -0.35)), "B", fontsize=FS + 1, style="italic", ha="center")
    ax.text(*(c + P(0, 0.35)), "C", fontsize=FS + 1, style="italic", ha="center")
    length_label(ax, a, b, "5 cm", c, dist=0.38)
    frame(ax, [a, P(6.6 * s, 0), c], pad=0.6)
    save(fig, "con_warmup3_sixty.png")


def warmup4_tangent():
    s = 0.3
    o = P(0, 0)
    p = P(0, -5 * s)
    q = p + P(12 * s, 0)
    fig, ax = new_axes(6, 3.6)
    ax.add_patch(Circle(o, 5 * s, fill=False, edgecolor="k", lw=LW))
    seg(ax, p + P(-1.0, 0), q + P(0.5, 0))
    seg(ax, o, p, lw=1.4)
    dot(ax, o)
    dot(ax, p)
    dot(ax, q)
    ax.text(*(o + P(0.0, 0.3)), "O", fontsize=FS + 1, style="italic", ha="center")
    ax.text(*(p + P(-0.25, -0.35)), "P", fontsize=FS + 1, style="italic", ha="center")
    ax.text(*(q + P(0.1, -0.38)), "Q", fontsize=FS + 1, style="italic", ha="center")
    length_label(ax, o, p, "5", q, dist=0.3)
    length_label(ax, p, q, "12", o, dist=0.35)
    frame(ax, [P(-1.6, 1.6), q + P(0.5, -0.6)], pad=0.3)
    save(fig, "con_warmup4_tangent.png")


def workout1_incircle():
    s = 0.3
    b, c = P(0, 0), P(14 * s, 0)
    a = P(5 * s, 12 * s)  # |AB| = 13, |AC| = 15, height 12
    foot = P(5 * s, 0)
    fig, ax = new_axes(5, 4.6)
    poly(ax, a, b, c)
    seg(ax, a, foot, lw=1.2, ls=(0, (5, 4)))
    right_angle(ax, foot, c, a, s=0.2)
    centre = (a + b + c) / 3
    length_label(ax, a, b, "13", centre, dist=0.35)
    length_label(ax, a, c, "15", centre, dist=0.35)
    length_label(ax, b, c, "14", a, dist=0.35)
    ax.text(*((a + foot) / 2 + P(0.28, 0)), "12", fontsize=FS - 1, va="center")
    names(ax, [a, b, c], "ABC")
    frame(ax, [a, b, c], pad=0.6)
    save(fig, "con_workout1_incircle.png")


def workout2_circumcentre():
    a, b, c = P(-4, 0), P(4, 0), P(0, 8)
    fig, ax = new_axes(4.6, 5)
    axes(ax, -5.5, 5.5, -1.2, 9.5)
    poly(ax, a, b, c)
    coord_label(ax, a, r"$A(-4,0)$", -0.3, 0.55)
    coord_label(ax, b, r"$B(4,0)$", 0.3, 0.55)
    coord_label(ax, c, r"$C(0,8)$", 1.4, 0.2)
    frame(ax, [P(-5.5, -1.2), P(5.5, 9.5)], pad=0.2)
    save(fig, "con_workout2_circumcentre.png")


def workout3_centroid_coords():
    a, b, c = P(0, 0), P(10, 2), P(2, 10)
    fig, ax = new_axes(4.8, 4.8)
    axes(ax, -1.2, 11.8, -1.2, 11.8)
    poly(ax, a, b, c)
    coord_label(ax, a, r"$A(0,0)$", -1.0, 0.9)
    coord_label(ax, b, r"$B(10,2)$", 0.0, -0.75)
    coord_label(ax, c, r"$C(2,10)$", 1.5, 0.3)
    frame(ax, [P(-1.2, -1.2), P(11.8, 11.8)], pad=0.2)
    save(fig, "con_workout3_centroid_coords.png")


def workout4_orthocentre():
    a, b, c = P(0, 0), P(6, 0), P(2, 4)
    fig, ax = new_axes(5, 3.8)
    axes(ax, -1.2, 7.5, -1.2, 5.5)
    poly(ax, a, b, c)
    coord_label(ax, a, r"$A(0,0)$", -0.6, 0.5)
    coord_label(ax, b, r"$B(6,0)$", 0.4, 0.5)
    coord_label(ax, c, r"$C(2,4)$", -0.2, 0.55)
    frame(ax, [P(-1.2, -1.2), P(7.5, 5.5)], pad=0.2)
    save(fig, "con_workout4_orthocentre.png")


def stretch1_parallelogram():
    s = 0.5
    a, b = P(0, 0), P(8 * s, 0)
    d = polar(5 * s, 60)
    c = b + d
    fig, ax = new_axes(5.6, 3.2)
    poly(ax, a, b, c, d)
    angle_mark(ax, a, b, d, r"$60^\circ$", r=0.45, text_r=0.85)
    centre = (a + c) / 2
    length_label(ax, a, b, "8 cm", centre, dist=0.35)
    length_label(ax, a, d, "5 cm", centre, dist=0.45)
    names(ax, [a, b, c, d], "ABCD")
    frame(ax, [a, b, c, d], pad=0.6)
    save(fig, "con_stretch1_parallelogram.png")


def stretch2_7_24_25():
    s = 0.2
    a, b, c = P(0, 7 * s), P(0, 0), P(24 * s, 0)
    fig, ax = new_axes(6, 2.8)
    poly(ax, a, b, c)
    centre = (a + b + c) / 3
    length_label(ax, a, b, "7", c, dist=0.3)
    length_label(ax, b, c, "24", a, dist=0.3)
    length_label(ax, a, c, "25", b, dist=0.3)
    names(ax, [a, b, c], "ABC")
    frame(ax, [a, b, c], pad=0.6)
    save(fig, "con_stretch2_7_24_25.png")


def stretch3_equilateral():
    s = 0.6
    b, c = P(0, 0), P(6 * s, 0)
    a = P(3 * s, 3 * np.sqrt(3) * s)
    fig, ax = new_axes(4, 3.8)
    poly(ax, a, b, c)
    centre = (a + b + c) / 3
    for p, q in ((a, b), (b, c), (c, a)):
        length_label(ax, p, q, "6 cm", centre, dist=0.6)
    names(ax, [a, b, c], "ABC")
    frame(ax, [a, b, c], pad=0.8)
    save(fig, "con_stretch3_equilateral.png")


def stretch4_tangent_coords():
    o, r = P(2, 1), np.sqrt(20)
    p = P(6, 3)
    fig, ax = new_axes(5, 5)
    axes(ax, -3.2, 8.5, -4.2, 6.8)
    ax.add_patch(Circle(o, r, fill=False, edgecolor="k", lw=LW))
    seg(ax, o, p, lw=1.4)
    coord_label(ax, o, r"$C(2,1)$", 0.0, -0.55)
    coord_label(ax, p, r"$P(6,3)$", 1.0, 0.35)
    frame(ax, [P(-3.2, -4.2), P(8.5, 6.8)], pad=0.2)
    save(fig, "con_stretch4_tangent_coords.png")


if __name__ == "__main__":
    warmup1_centroid()
    warmup2_right_triangle()
    warmup3_sixty()
    warmup4_tangent()
    workout1_incircle()
    workout2_circumcentre()
    workout3_centroid_coords()
    workout4_orthocentre()
    stretch1_parallelogram()
    stretch2_7_24_25()
    stretch3_equilateral()
    stretch4_tangent_coords()
