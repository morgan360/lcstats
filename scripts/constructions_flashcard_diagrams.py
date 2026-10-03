"""Draw the front-of-card figures for the two Constructions flashcard sets.

Writes PNGs to media/flashcards/front/con_*.png (git-ignored; this script is
the source of truth). FILES maps (set title, card order) to a figure; attach
locally, then reach production through export_flashcards --include-images and
import_flashcards.

"Which centre is this?" cards show the construction lines meeting. "What is the
first step?" cards show only the starting figure, and "why does it work?" cards
show the finished construction, so no card's figure gives away its answer.

    python scripts/constructions_flashcard_diagrams.py
"""
import numpy as np
from matplotlib.patches import Circle

import geometry_flashcard_diagrams as gf  # sets the card-sized OUT, LW and FS
import geometry_theorem_diagrams as g
from geometry_theorem_diagrams import (
    P, polar, seg, poly, dot, point_label, angle_mark, right_angle, tick,
    frame, new_axes,
)

FS = gf.FS
CENTRES = "Constructions: Centres & Definitions"
STEPS = "Constructions: Step by Step"
save, label = gf.save, gf.label
L = np.linalg.norm
TRI = (P(1.0, 2.6), P(0, 0), P(3.6, 0))  # A, B, C: a scalene, acute triangle


def perp(v):
    return P(-v[1], v[0])


def meet(p1, d1, p2, d2):
    t = np.linalg.solve(np.column_stack([d1, -d2]), p2 - p1)[0]
    return p1 + t * d1


def foot(p, a, b):
    d = (b - a) / L(b - a)
    return a + np.dot(p - a, d) * d


def names(ax, pts, letters="ABC", dist=0.36):
    centre = sum(pts) / len(pts)
    for p, n in zip(pts, letters):
        point_label(ax, p, n, centre, dist=dist)


def thin(ax, p, q):
    seg(ax, p, q, lw=1.5, ls=(0, (4, 3)))


def base_triangle(w=3.6, h=2.8, tri=TRI):
    fig, ax = new_axes(w, h)
    poly(ax, *tri)
    names(ax, list(tri))
    return fig, ax


def circumcentre(a, b, c):
    return meet((a + b) / 2, perp(b - a), (b + c) / 2, perp(c - b))


def incentre(a, b, c):
    u = lambda p, q, r: (q - p) / L(q - p) + (r - p) / L(r - p)
    return meet(a, u(a, b, c), b, u(b, a, c))


def draw_perp_bisectors(ax, tri, circle=False):
    a, b, c = tri
    o = circumcentre(a, b, c)
    for p, q in ((a, b), (b, c), (c, a)):
        m = (p + q) / 2
        d = perp(q - p) / L(q - p)
        s = 1 if np.dot(o - m, d) >= 0 else -1
        thin(ax, m - 0.4 * s * d, o + 0.4 * s * d)
        right_angle(ax, m, q, m + s * d, s=0.14)
        tick(ax, p, m, s=0.11)
        tick(ax, m, q, s=0.11)
    dot(ax, o)
    if circle:
        ax.add_patch(Circle(o, L(o - a), fill=False, edgecolor="k", lw=1.6))
    return o


def draw_angle_bisectors(ax, tri):
    a, b, c = tri
    i = incentre(a, b, c)
    for v, p, q in ((a, b, c), (b, c, a), (c, a, b)):
        thin(ax, v, i + 0.25 * (i - v) / L(i - v))
        angle_mark(ax, v, p, i, "", r=0.32)
        angle_mark(ax, v, i, q, "", r=0.38)
    dot(ax, i)
    return i


def draw_medians(ax, tri):
    a, b, c = tri
    for v, p, q in ((a, b, c), (b, c, a), (c, a, b)):
        m = (p + q) / 2
        thin(ax, v, m)
        tick(ax, p, m, s=0.11)
        tick(ax, m, q, s=0.11)
    dot(ax, (a + b + c) / 3)


def draw_altitudes(ax, tri):
    a, b, c = tri
    for v, p, q in ((a, b, c), (b, c, a), (c, a, b)):
        f = foot(v, p, q)
        thin(ax, v, f)
        right_angle(ax, f, q if L(q - f) > 0.2 else p, v, s=0.14)
    h = meet(a, perp(c - b), c, perp(b - a))
    dot(ax, h)


def c01_circumcentre():
    fig, ax = base_triangle()
    draw_perp_bisectors(ax, TRI)
    frame(ax, list(TRI), pad=0.55)
    return save(fig, "con_c01_perp_bisectors.png")


def c02_incentre():
    fig, ax = base_triangle()
    draw_angle_bisectors(ax, TRI)
    frame(ax, list(TRI), pad=0.55)
    return save(fig, "con_c02_angle_bisectors.png")


def c03_centroid():
    fig, ax = base_triangle()
    draw_medians(ax, TRI)
    frame(ax, list(TRI), pad=0.55)
    return save(fig, "con_c03_medians.png")


def c04_orthocentre():
    fig, ax = base_triangle()
    draw_altitudes(ax, TRI)
    frame(ax, list(TRI), pad=0.55)
    return save(fig, "con_c04_altitudes.png")


RIGHT = (P(0, 2.4), P(0, 0), P(3.4, 0))  # right angle at B
OBTUSE = (P(0.8, 0.9), P(0, 0), P(3.8, 0))  # obtuse angle at A, about 115 degrees


def c08_right():
    fig, ax = base_triangle(tri=RIGHT)
    right_angle(ax, RIGHT[1], RIGHT[0], RIGHT[2], s=0.22)
    frame(ax, list(RIGHT), pad=0.55)
    return save(fig, "con_c08_right.png")


def c10_obtuse():
    fig, ax = base_triangle(w=4.0, h=2.2, tri=OBTUSE)
    frame(ax, list(OBTUSE), pad=0.55)
    return save(fig, "con_c10_obtuse.png")


def s_triangle_plain():
    fig, ax = base_triangle()
    frame(ax, list(TRI), pad=0.55)
    return save(fig, "con_s_triangle.png")


def s16_after():
    fig, ax = base_triangle(w=3.6, h=3.4)
    o = draw_perp_bisectors(ax, TRI, circle=True)
    r = L(o - TRI[0])
    frame(ax, [o + P(-r, -r), o + P(r, r)], pad=0.3)
    return save(fig, "con_s16_after.png")


def s17_after():
    fig, ax = base_triangle()
    a, b, c = TRI
    i = draw_angle_bisectors(ax, TRI)
    f = foot(i, b, c)
    seg(ax, i, f, lw=2.0)
    right_angle(ax, f, c, i, s=0.13)
    frame(ax, list(TRI), pad=0.55)
    return save(fig, "con_s17_after.png")


def s18(after):
    fig, ax = new_axes(3.6, 2.6)
    a = P(0, 0)
    r = 2.0
    seg(ax, a, P(3.0, 0))
    dot(ax, a)
    label(ax, a, "A", dx=-0.25, dy=-0.3)
    pts = [a, P(3.0, 0), P(0, 2.3)]
    if after:
        b = P(r, 0)
        c = polar(r, 60)
        for centre, a0, a1 in ((a, -5, 75), (b, 105, 185)):
            t = np.radians(np.linspace(a0, a1, 80))
            ax.plot(centre[0] + r * np.cos(t), centre[1] + r * np.sin(t), color="k", lw=1.2)
        seg(ax, a, c + 0.35 * (c - a) / L(c - a))
        for p, n, dx, dy in ((b, "B", 0.15, -0.32), (c, "C", -0.3, 0.2)):
            dot(ax, p)
            label(ax, p, n, dx=dx, dy=dy)
    frame(ax, pts, pad=0.4)
    return save(fig, f"con_s18_{'after' if after else 'before'}.png")


def s19(after):
    fig, ax = new_axes(3.4, 3.0)
    o, r = P(0, 0), 1.3
    p = polar(r, -50)
    ax.add_patch(Circle(o, r, fill=False, edgecolor="k", lw=g.LW))
    dot(ax, o)
    dot(ax, p)
    label(ax, o, "O", dx=-0.25, dy=0.2)
    label(ax, p, "P", dx=0.32, dy=-0.2)
    if after:
        d = (p - o) / L(p - o)
        seg(ax, o, p + 0.7 * d, lw=1.5, ls=(0, (4, 3)))
        t = perp(d)
        seg(ax, p - 1.4 * t, p + 1.4 * t)
        right_angle(ax, p, o, p + t, s=0.16)
    frame(ax, [P(-1.6, -2.0), P(2.4, 1.6)], pad=0.2)
    return save(fig, f"con_s19_{'after' if after else 'before'}.png")


def s20_arcs():
    """Parallelogram construction: [AB] and [AD] drawn; arcs from D and B locate C."""
    fig, ax = new_axes(4.2, 2.6)
    a, b = P(0, 0), P(3.0, 0)
    d = polar(1.8, 60)
    c = b + d
    seg(ax, a, b)
    seg(ax, a, d)
    angle_mark(ax, a, b, d, "", r=0.35)
    for centre, rad, a0, a1 in ((d, 3.0, -15, 15), (b, 1.8, 45, 75)):
        t = np.radians(np.linspace(a0, a1, 40))
        ax.plot(centre[0] + rad * np.cos(t), centre[1] + rad * np.sin(t), color="k", lw=1.2)
    for p, n, dx, dy in ((a, "A", -0.25, -0.25), (b, "B", 0.2, -0.3), (d, "D", -0.25, 0.25)):
        dot(ax, p)
        label(ax, p, n, dx=dx, dy=dy)
    frame(ax, [a, b, c + P(0.3, 0.3), d], pad=0.45)
    return save(fig, "con_s20_arcs.png")


def s21_bisector_vs_median():
    """Centroid: the perpendicular bisector of [BC] finds M; the median joins A to M."""
    fig, ax = base_triangle()
    a, b, c = TRI
    m = (b + c) / 2
    thin(ax, m + P(0, -0.5), m + P(0, 2.2))
    right_angle(ax, m, c, m + P(0, 1), s=0.14)
    tick(ax, b, m, s=0.11)
    tick(ax, m, c, s=0.11)
    dot(ax, m)
    label(ax, m, "M", dx=0.28, dy=-0.3)
    frame(ax, list(TRI) + [m + P(0, 2.2)], pad=0.55)
    return save(fig, "con_s21_bisector.png")


def s22_obtuse_altitude():
    """Orthocentre of an obtuse triangle: the foot from C lands on [BA] extended."""
    fig, ax = new_axes(4.2, 2.6)
    a, b, c = P(1.2, 0), P(0, 0), P(2.6, 1.6)  # obtuse angle at A
    poly(ax, a, b, c)
    names(ax, [a, b, c])
    frame(ax, [a, b, c, P(3.2, 0)], pad=0.55)
    return save(fig, "con_s22_obtuse.png")


def build():
    c1, c2, c3, c4 = c01_circumcentre(), c02_incentre(), c03_centroid(), c04_orthocentre()
    right, obtuse = c08_right(), c10_obtuse()
    centres = {1: c1, 2: c2, 3: c3, 4: c4, 8: right, 9: right, 10: obtuse}
    files = {(CENTRES, i): n for i, n in centres.items()}
    plain = s_triangle_plain()
    steps = [plain, s16_after(), s16_after(), plain, s17_after(), s18(False), s18(True),
             s19(False), s19(True), s20_arcs(), s21_bisector_vs_median(), plain,
             s22_obtuse_altitude()]
    files.update({(STEPS, i): n for i, n in enumerate(steps, 1)})
    return files


if __name__ == "__main__":
    build()
