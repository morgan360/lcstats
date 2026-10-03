"""Draw the front-of-card figures for the two Geometry-Theorems flashcard sets.

Writes PNGs to media/flashcards/front/geo_*.png, git-ignored like the rest of
media/, so this script is the source of truth. FILES at the bottom maps each
(set title, card order) to its figure; attach them locally, then reach
production through export_flashcards --include-images and import_flashcards,
which matches cards on external_id and updates them in place.

The study page shows the figure under the question at no more than 200px tall,
so these are compact, with heavier lines and larger labels than the practice
question diagrams. Same rule as those: label only what the card states. In
particular, a "what is the construction?" card shows the figure *before* the
construction, and the 5-12-13 triangle carries no right-angle mark.

    python scripts/geometry_flashcard_diagrams.py
"""
from pathlib import Path

import numpy as np
from matplotlib.patches import Circle, Polygon

import geometry_theorem_diagrams as g
from geometry_theorem_diagrams import (
    P, polar, seg, poly, dot, point_label, angle_mark, right_angle, tick,
    parallel_arrow, length_label, frame, new_axes,
)

g.OUT = Path(__file__).resolve().parent.parent / "media" / "flashcards" / "front"
g.LW = 2.4
g.FS = 22
FS = g.FS

WHICH = "Geometry: Which Theorem?"
PROOF = "Geometry: Proof Jigsaw"


def save(fig, name):
    g.save(fig, name)
    return name


def label(ax, p, text, dx=0, dy=0, fs=None):
    ax.text(p[0] + dx, p[1] + dy, text, fontsize=fs or FS + 1, ha="center",
            va="center", style="italic")


def triangle(a, b, c, names="ABC", ax=None):
    poly(ax, a, b, c)
    centre = (a + b + c) / 3
    for p, n in zip((a, b, c), names):
        point_label(ax, p, n, centre, dist=0.4)


# ---------------------------------------------------------------- Which Theorem?

def w01_isosceles():
    fig, ax = new_axes(3.2, 3.2)
    a, b, c = P(1.25, 3), P(0, 0), P(2.5, 0)
    triangle(a, b, c, ax=ax)
    tick(ax, a, b, s=0.16)
    tick(ax, a, c, s=0.16)
    frame(ax, [a, b, c], pad=0.6)
    return save(fig, "geo_w01_isosceles.png")


def w02_alternate():
    fig, ax = new_axes(4.2, 2.6)
    p = P(1.4, 1.6)
    q = p + 1.6 / np.sin(np.radians(60)) * polar(1, -60)
    for y, name in ((p[1], r"$l$"), (0, r"$m$")):
        seg(ax, P(-0.4, y), P(3.8, y))
        ax.text(4.0, y, name, fontsize=FS + 2, va="center")
    d = (q - p) / np.linalg.norm(q - p)
    seg(ax, p - 0.6 * d, q + 0.6 * d)
    angle_mark(ax, p, P(3.8, p[1]), q, r"$x$", r=0.35, text_r=0.75)
    angle_mark(ax, q, P(-0.4, 0), p, r"$x$", r=0.35, text_r=0.75)
    frame(ax, [P(-0.4, -0.7), P(4.3, 2.3)], pad=0.15)
    return save(fig, "geo_w02_alternate.png")


def w03_crossing():
    fig, ax = new_axes(3, 3)
    o = P(0, 0)
    e = [polar(1.8, 20), polar(1.8, 200), polar(1.8, 92), polar(1.8, 272)]
    seg(ax, e[0], e[1])
    seg(ax, e[2], e[3])
    angle_mark(ax, o, e[0], e[2], r"$72^\circ$", r=0.4, text_r=0.95)
    angle_mark(ax, o, e[1], e[3], r"$?$", r=0.4, text_r=0.8)
    frame(ax, e, pad=0.2)
    return save(fig, "geo_w03_crossing.png")


def w04_5_12_13():
    s = 0.25
    fig, ax = new_axes(4, 2.4)
    b, c = P(0, 0), P(12 * s, 0)
    a = P(0, 5 * s)
    poly(ax, a, b, c)
    length_label(ax, a, b, "5", c, dist=0.35)
    length_label(ax, b, c, "12", a, dist=0.35)
    length_label(ax, a, c, "13", b, dist=0.35)
    frame(ax, [a, b, c], pad=0.6)
    return save(fig, "geo_w04_5_12_13.png")


def w05_8_15():
    s = 0.2
    fig, ax = new_axes(4, 2.4)
    b, c, a = P(0, 0), P(15 * s, 0), P(0, 8 * s)
    poly(ax, a, b, c)
    right_angle(ax, b, a, c, s=0.25)
    length_label(ax, a, b, "8", c, dist=0.35)
    length_label(ax, b, c, "15", a, dist=0.35)
    length_label(ax, a, c, "?", b, dist=0.35)
    frame(ax, [a, b, c], pad=0.6)
    return save(fig, "geo_w05_8_15.png")


def w06_exterior():
    fig, ax = new_axes(4, 2.8)
    # interior angles 60 (at B), 70 (at A), 50 (at C); exterior at C = 130
    k = 2.6
    b = P(0, 0)
    c = P(k * np.sin(np.radians(70)), 0)
    a = b + k * np.sin(np.radians(50)) * polar(1, 60)
    d = c + P(1.4, 0)
    poly(ax, a, b, c)
    seg(ax, c, d)
    angle_mark(ax, b, c, a, r"$60^\circ$", r=0.35, text_r=0.85, fs=FS - 3)
    angle_mark(ax, a, b, c, r"$x$", r=0.35, text_r=0.75)
    angle_mark(ax, c, a, d, r"$130^\circ$", r=0.3, text_r=0.9, fs=FS - 3)
    frame(ax, [a, b, d], pad=0.45)
    return save(fig, "geo_w06_exterior.png")


def parallelogram_pts(w=3.2, side=1.9, deg=70):
    a, b = P(0, 0), P(w, 0)
    d = polar(side, deg)
    return a, b, b + d, d


def w07_diagonals():
    fig, ax = new_axes(4.2, 2.6)
    a, b, c, d = parallelogram_pts()
    e = (a + c) / 2
    poly(ax, a, b, c, d)
    seg(ax, a, c, lw=1.6)
    seg(ax, b, d, lw=1.6)
    for p, n in zip((a, b, c, d), "ABCD"):
        point_label(ax, p, n, e, dist=0.4)
    label(ax, e, "E", dy=-0.38)
    ax.text(*((a + e) / 2 + P(0.05, 0.32)), "7", fontsize=FS, ha="center", va="center")
    frame(ax, [a, b, c, d], pad=0.5)
    return save(fig, "geo_w07_diagonals.png")


def w08_ratio():
    fig, ax = new_axes(3.6, 3)
    a, b, c = P(1.2, 3), P(0, 0), P(3.4, 0)
    x = a + 0.4 * (b - a)
    y = a + 0.4 * (c - a)
    triangle(a, b, c, ax=ax)
    seg(ax, x, y)
    parallel_arrow(ax, x, y, s=0.18)
    parallel_arrow(ax, b, c, s=0.18)
    centre = (a + b + c) / 3
    length_label(ax, a, x, "2", centre, dist=0.35)
    length_label(ax, x, b, "3", centre, dist=0.35)
    frame(ax, [a, b, c], pad=0.6)
    return save(fig, "geo_w08_ratio.png")


def w09_similar():
    fig, ax = new_axes(5, 2.4)
    a, b, c = P(0.5, 1.5), P(0, 0), P(2, 0)
    t = P(3.4, 0)
    s = 0.7
    d, e, f = t + s * a, t + s * b, t + s * c
    triangle(a, b, c, "ABC", ax=ax)
    triangle(d, e, f, "DEF", ax=ax)
    for v, p, q in ((a, b, c), (d, e, f)):
        angle_mark(ax, v, p, q, "", r=0.22)
    for v, p, q in ((b, c, a), (e, f, d)):
        angle_mark(ax, v, p, q, "", r=0.22)
        angle_mark(ax, v, p, q, "", r=0.29)
    frame(ax, [a, b, c, d, e, f], pad=0.5)
    return save(fig, "geo_w09_similar.png")


def w10_cannot_close():
    fig, ax = new_axes(4.4, 2)
    s = 0.45
    b, c = P(0, 0), P(8 * s, 0)
    seg(ax, b, c)
    # The 3 and the 4 swung up as far as they go, still short of meeting.
    p3 = b + 3 * s * polar(1, 35)
    p4 = c + 4 * s * polar(1, 150)
    seg(ax, b, p3)
    seg(ax, c, p4)
    for p, r, a0, a1 in ((b, 3 * s, 0, 90), (c, 4 * s, 90, 180)):
        t = np.radians(np.linspace(a0, a1, 60))
        ax.plot(p[0] + r * np.cos(t), p[1] + r * np.sin(t), color="k", lw=1,
                ls=(0, (3, 3)))
    length_label(ax, b, c, "8", P(1.8, 1), dist=0.3)
    length_label(ax, b, p3, "3", c, dist=0.3)
    length_label(ax, c, p4, "4", b, dist=0.3)
    frame(ax, [b, c, P(0, 1.9)], pad=0.4)
    return save(fig, "geo_w10_cannot_close.png")


def w11_pqr():
    fig, ax = new_axes(3.8, 2.6)
    p, q, r = P(0, 0), P(3.6, 0), P(1.0, 1.7)
    triangle(p, q, r, "PQR", ax=ax)
    frame(ax, [p, q, r], pad=0.55)
    return save(fig, "geo_w11_pqr.png")


def circle(ax, o, r):
    ax.add_patch(Circle(o, r, fill=False, edgecolor="k", lw=g.LW))
    dot(ax, o)


def w12_centre():
    fig, ax = new_axes(3, 3)
    o, r = P(0, 0), 1.6
    a, b, c = polar(r, 220), polar(r, 320), polar(r, 90)
    circle(ax, o, r)
    for p, q in ((c, a), (c, b), (o, a), (o, b)):
        seg(ax, p, q)
    angle_mark(ax, o, a, b, r"$80^\circ$", r=0.3, text_r=0.65, fs=FS - 4)
    for p, n in ((a, "A"), (b, "B"), (c, "C")):
        point_label(ax, p, n, o, dist=0.35)
    label(ax, o, "O", dx=0.3, dy=0.12)
    frame(ax, [P(-r, -r), P(r, r)], pad=0.45)
    return save(fig, "geo_w12_centre.png")


def foot(p, a, b):
    d = (b - a) / np.linalg.norm(b - a)
    return a + np.dot(p - a, d) * d


def w13_two_heights():
    fig, ax = new_axes(3.8, 2.8)
    a, b, c = P(1.1, 2.4), P(0, 0), P(3.4, 0)
    triangle(a, b, c, ax=ax)
    fa, fb = foot(a, b, c), foot(b, a, c)
    seg(ax, a, fa, lw=1.6, ls=(0, (4, 3)))
    seg(ax, b, fb, lw=1.6, ls=(0, (4, 3)))
    right_angle(ax, fa, c, a, s=0.18)
    right_angle(ax, fb, c, b, s=0.18)
    ax.text(*(a + 0.3 * (fa - a) + P(0.28, 0)), r"$h_1$", fontsize=FS - 2, va="center", ha="center")
    ax.text(*(b + 0.3 * (fb - b) + P(0.05, 0.32)), r"$h_2$", fontsize=FS - 2, va="center", ha="center")
    frame(ax, [a, b, c], pad=0.55)
    return save(fig, "geo_w13_two_heights.png")


def w14_halves():
    fig, ax = new_axes(4.2, 2.6)
    a, b, c, d = parallelogram_pts()
    ax.add_patch(Polygon([a, b, d], closed=True, facecolor="#dddddd", edgecolor="none"))
    poly(ax, a, b, c, d)
    seg(ax, b, d)
    centre = (a + c) / 2
    for p, n in zip((a, b, c, d), "ABCD"):
        point_label(ax, p, n, centre, dist=0.4)
    frame(ax, [a, b, c, d], pad=0.5)
    return save(fig, "geo_w14_halves.png")


def w15_three_parallels():
    fig, ax = new_axes(4.2, 2.8)
    ys = (2.2, 1.1, 0)
    for y in ys:
        seg(ax, P(-0.3, y), P(4, y))
        parallel_arrow(ax, P(-0.3, y), P(4, y), at=0.92, s=0.16)
    t1 = [P(0.6 + 0.25 * k, y) for k, y in enumerate(ys)]
    t2 = [P(2.0 + 0.7 * k, y) for k, y in enumerate(ys)]
    seg(ax, t1[0] + P(-0.1, 0.4), t1[2] + P(0.1, -0.4))
    seg(ax, t2[0] + P(-0.25, 0.35), t2[2] + P(0.25, -0.35))
    length_label(ax, t1[0], t1[1], "1.5", t2[0], dist=0.55)
    length_label(ax, t1[1], t1[2], "1.5", t2[0], dist=0.55)
    frame(ax, [P(-0.9, -0.5), P(4, 2.7)], pad=0.2)
    return save(fig, "geo_w15_three_parallels.png")


# ---------------------------------------------------------------- Proof Jigsaw

T_A, T_B, T_C = P(1.3, 2.4), P(0, 0), P(3.6, 0)


def p_t4(after):
    fig, ax = new_axes(4.2, 2.8)
    a, b, c = T_A, T_B, T_C
    poly(ax, a, b, c)
    label(ax, a, "A", dy=0.42)
    label(ax, b, "B", dx=-0.3, dy=-0.25)
    label(ax, c, "C", dx=0.3, dy=-0.25)
    pts = [a + P(0, 0.5), b, c]
    if after:
        l0, l1 = a + P(-1.5, 0), a + P(1.5, 0)
        seg(ax, l0, l1)
        parallel_arrow(ax, l0, l1, at=0.85, s=0.16)
        parallel_arrow(ax, b, c, at=0.75, s=0.16)
        angle_mark(ax, a, l0, b, r"$1$", r=0.3, text_r=0.62, fs=FS - 4)
        angle_mark(ax, a, b, c, r"$2$", r=0.38, text_r=0.68, fs=FS - 4)
        angle_mark(ax, a, c, l1, r"$3$", r=0.3, text_r=0.62, fs=FS - 4)
        angle_mark(ax, b, c, a, "", r=0.35)
        angle_mark(ax, c, a, b, "", r=0.35)
        angle_mark(ax, c, a, b, "", r=0.42)
        pts += [l0, l1]
    frame(ax, pts, pad=0.55)
    return save(fig, f"geo_p_t4_{'after' if after else 'before'}.png")


def p_t6():
    fig, ax = new_axes(4.4, 2.8)
    a, b, c = T_A, T_B, T_C
    d = c + P(1.4, 0)
    poly(ax, a, b, c)
    seg(ax, c, d)
    label(ax, a, "A", dy=0.38)
    label(ax, b, "B", dx=-0.3, dy=-0.25)
    label(ax, c, "C", dy=-0.4)
    label(ax, d, "D", dy=-0.38)
    angle_mark(ax, a, b, c, r"$1$", r=0.35, text_r=0.68, fs=FS - 4)
    angle_mark(ax, b, c, a, r"$2$", r=0.35, text_r=0.68, fs=FS - 4)
    angle_mark(ax, c, a, b, r"$3$", r=0.35, text_r=0.68, fs=FS - 4)
    angle_mark(ax, c, d, a, r"$4$", r=0.3, text_r=0.62, fs=FS - 4)
    frame(ax, [a, b, d], pad=0.55)
    return save(fig, "geo_p_t6.png")


def p_t9(after):
    fig, ax = new_axes(4.2, 2.6)
    a, b, c, d = parallelogram_pts()
    poly(ax, a, b, c, d)
    parallel_arrow(ax, a, b, s=0.16)
    parallel_arrow(ax, d, c, s=0.16)
    parallel_arrow(ax, a, d, n=2, s=0.16)
    parallel_arrow(ax, b, c, n=2, s=0.16)
    if after:
        seg(ax, a, c, lw=1.8)
    centre = (a + c) / 2
    for p, n in zip((a, b, c, d), "ABCD"):
        point_label(ax, p, n, centre, dist=0.4)
    frame(ax, [a, b, c, d], pad=0.5)
    return save(fig, f"geo_p_t9_{'after' if after else 'before'}.png")


def p_t14(after):
    fig, ax = new_axes(4.2, 2.6)
    # Right angle at C, on top; hypotenuse [AB] along the bottom.
    a, b = P(0, 0), P(4, 0)
    c = P(1.44, 1.92)  # angle ACB = 90: (c-a).(c-b) = 0
    triangle(a, b, c, "ABC", ax=ax)
    right_angle(ax, c, a, b, s=0.22)
    if after:
        dd = foot(c, a, b)
        seg(ax, c, dd, lw=1.8)
        right_angle(ax, dd, b, c, s=0.2)
        label(ax, dd, "D", dy=-0.38)
    frame(ax, [a, b, c], pad=0.55)
    return save(fig, f"geo_p_t14_{'after' if after else 'before'}.png")


def p_t19(after):
    fig, ax = new_axes(3.2, 3.2)
    o, r = P(0, 0), 1.6
    a, b, c = polar(r, 205), polar(r, 335), polar(r, 100)
    circle(ax, o, r)
    for p, q in ((c, a), (c, b), (o, a), (o, b)):
        seg(ax, p, q)
    for p, n in ((a, "A"), (b, "B"), (c, "C")):
        point_label(ax, p, n, o, dist=0.35)
    if after:
        d = -c
        seg(ax, c, d, lw=1.8)
        point_label(ax, d, "D", o, dist=0.35)
        angle_mark(ax, a, o, c, r"$x$", r=0.3, text_r=0.6, fs=FS - 1)
        angle_mark(ax, c, a, o, r"$x$", r=0.5, text_r=0.95, fs=FS - 1)
        angle_mark(ax, b, c, o, r"$y$", r=0.3, text_r=0.6, fs=FS - 1)
        angle_mark(ax, c, o, b, r"$y$", r=0.5, text_r=0.95, fs=FS - 1)
        label(ax, o, "O", dx=0.32, dy=0.05)
    else:
        label(ax, o, "O", dx=0.0, dy=-0.32)
    frame(ax, [P(-r, -r), P(r, r)], pad=0.45)
    return save(fig, f"geo_p_t19_{'after' if after else 'before'}.png")


def build():
    which = [w01_isosceles(), w02_alternate(), w03_crossing(), w04_5_12_13(),
             w05_8_15(), w06_exterior(), w07_diagonals(), w08_ratio(),
             w09_similar(), w10_cannot_close(), w11_pqr(), w12_centre(),
             w13_two_heights(), w14_halves(), w15_three_parallels()]
    t4b, t4a, t6 = p_t4(False), p_t4(True), p_t6()
    t9b, t9a = p_t9(False), p_t9(True)
    t14b, t14a = p_t14(False), p_t14(True)
    t19b, t19a = p_t19(False), p_t19(True)
    files = {(WHICH, i): name for i, name in enumerate(which, 1)}
    proof = [t4b, t4a, t4a, t6, t6, t6, t9b, t9a, t9a,
             t14b, t14a, t14a, t19b, t19a, t19a]
    files.update({(PROOF, i): name for i, name in enumerate(proof, 1)})
    return files


if __name__ == "__main__":
    build()
