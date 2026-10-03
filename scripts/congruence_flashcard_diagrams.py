"""Draw the front-of-card figures for the two Congruence & Proof flashcard sets.

Writes PNGs to media/flashcards/front/cp_*.png (git-ignored; this script is the
source of truth). FILES maps (set title, card order) to a figure. Attach them
locally, then reach production through export_flashcards --include-images and
import_flashcards, which updates cards in place by external_id.

Sizing and labelling follow geometry_flashcard_diagrams.py: compact, heavy
lines, only what the card states, and a "what is the construction?" card shows
the figure before the construction. The proofs of Theorems 11-13 follow the
lettering of the Active Maths 4 slides students learn them from.

    python scripts/congruence_flashcard_diagrams.py
"""
import numpy as np

import geometry_flashcard_diagrams as gf  # sets the card-sized OUT, LW and FS
from geometry_theorem_diagrams import (
    P, polar, seg, poly, angle_mark, right_angle, tick, parallel_arrow,
    point_label, new_axes, frame,
)

FS = gf.FS
KEY = "Congruence & Proof: Key Ideas"
PROOF = "Congruence & Proof: Proof Jigsaw"
save, label = gf.save, gf.label


def names(ax, pts, letters, dist=0.38):
    centre = sum(pts) / len(pts)
    for p, n in zip(pts, letters):
        point_label(ax, p, n, centre, dist=dist)


def pair(marks, shape=((0, 0), (2.4, 0), (0.7, 1.6)), mirror=True, letters=("ABC", "DEF")):
    """Two congruent triangles side by side, the second mirrored, with marks.

    marks: list of ("side", i, j, n) for n ticks on side ij, ("angle", i, n)
    for n arcs at vertex i, or ("right", i).
    """
    fig, ax = new_axes(4.8, 2.2)
    t1 = [P(*p) for p in shape]
    t2 = [P(6.2 - p[0], p[1]) if mirror else P(p[0] + 3.4, p[1]) for p in shape]
    for tri, lets in ((t1, letters[0]), (t2, letters[1])):
        poly(ax, *tri)
        names(ax, tri, lets)
        for m in marks:
            if m[0] == "side":
                tick(ax, tri[m[1]], tri[m[2]], n=m[3], s=0.15)
            elif m[0] == "angle":
                i = m[1]
                for k in range(m[2]):
                    angle_mark(ax, tri[i], tri[(i + 1) % 3], tri[(i + 2) % 3], "", r=0.28 + 0.08 * k)
            elif m[0] == "right":
                i = m[1]
                right_angle(ax, tri[i], tri[(i + 1) % 3], tri[(i + 2) % 3], s=0.2)
    frame(ax, t1 + t2, pad=0.45)
    return fig


def k01_sss():
    fig = pair([("side", 0, 1, 1), ("side", 1, 2, 2), ("side", 2, 0, 3)])
    return save(fig, "cp_k01_sss.png")


def k02_sas():
    # sides BA and BC with the angle at B between them (vertex index 1)
    fig = pair([("side", 0, 1, 1), ("side", 1, 2, 2), ("angle", 1, 1)])
    return save(fig, "cp_k02_sas.png")


def k03_asa():
    fig = pair([("angle", 0, 1), ("angle", 1, 2), ("side", 0, 1, 1)])
    return save(fig, "cp_k03_asa.png")


def k04_rhs():
    # right angle at A (index 0); hypotenuse BC; one other side AB
    fig = pair([("right", 0), ("side", 1, 2, 2), ("side", 0, 1, 1)],
               shape=((0, 0), (2.4, 0), (0, 1.6)))
    return save(fig, "cp_k04_rhs.png")


def k05_ssa():
    """Two different triangles with the same two sides and non-included angle."""
    fig, ax = new_axes(4.4, 2.2)
    ang_b, ab, ac = 32, 2.8, 1.75
    # C on the ray from B along the x-axis with |AC| = ac: two solutions
    a = polar(ab, ang_b)
    disc = np.sqrt(ac ** 2 - a[1] ** 2)
    c1, c2 = P(a[0] - disc, 0), P(a[0] + disc, 0)
    shift = P(3.0, 0)
    t1 = [a, P(0, 0), c1]
    t2 = [a + shift, shift, c2 + shift]
    for tri, lets in ((t1, "ABC"), (t2, "DEF")):
        poly(ax, *tri)
        names(ax, tri, lets)
        tick(ax, tri[0], tri[1], n=1, s=0.15)
        tick(ax, tri[0], tri[2], n=2, s=0.15)
        angle_mark(ax, tri[1], tri[2], tri[0], "", r=0.4)
    frame(ax, t1 + t2, pad=0.45)
    return save(fig, "cp_k05_ssa.png")


def k06_aaa():
    fig, ax = new_axes(4.4, 2.2)
    base = [P(0, 0), P(2.0, 0), P(0.6, 1.3)]
    small = [P(3.5, 0) + 0.6 * p for p in base]
    for tri, lets in ((base, "ABC"), (small, "DEF")):
        poly(ax, *tri)
        names(ax, tri, lets)
        for i, n in ((0, 1), (1, 2), (2, 3)):
            for k in range(n):
                angle_mark(ax, tri[i], tri[(i + 1) % 3], tri[(i + 2) % 3], "", r=0.2 + 0.06 * k)
    frame(ax, base + small, pad=0.45)
    return save(fig, "cp_k06_aaa.png")


def k07_kite():
    fig, ax = new_axes(4, 2.4)
    a, c = P(0, 0), P(3.4, 0)
    b, d = P(1.1, 1.0), P(1.1, -1.0)
    poly(ax, a, b, c, d)
    seg(ax, a, c, lw=1.6, ls=(0, (4, 3)))
    tick(ax, a, b, s=0.15)
    tick(ax, a, d, s=0.15)
    tick(ax, c, b, n=2, s=0.15)
    tick(ax, c, d, n=2, s=0.15)
    names(ax, [a, b, c, d], "ABCD")
    frame(ax, [a, b, c, d], pad=0.45)
    return save(fig, "cp_k07_kite.png")


def p_t11(after):
    """Theorem 11, lettered as in the slides: AD, BE, CF parallel; |AB| = |BC|."""
    fig, ax = new_axes(5.4, 2.8)
    ys = (2, 1, 0)
    d, e, f = P(0, 2), P(-0.5, 1), P(-1, 0)
    a, b, c = P(3, 2), P(4, 1), P(5, 0)
    for y in ys:
        seg(ax, P(-1.6, y), P(5.6, y), lw=1.8)
        parallel_arrow(ax, P(-1.6, y), P(5.6, y), at=0.95, s=0.14)
    seg(ax, d + P(0.25, 0.5), f + P(-0.25, -0.5))
    seg(ax, a + P(-0.3, 0.3), c + P(0.3, -0.3))
    tick(ax, a, b, s=0.14)
    tick(ax, b, c, s=0.14)
    for p, n in ((d, "D"), (e, "E"), (f, "F")):
        label(ax, p, n, dx=-0.32, dy=0.22)
    for p, n in ((a, "A"), (b, "B"), (c, "C")):
        label(ax, p, n, dx=0.32, dy=0.22)
    if after:
        e1, f1, b1 = P(2.5, 1), P(2, 0), P(1, 1)
        seg(ax, a, f1, lw=1.8, ls=(0, (4, 3)))
        seg(ax, f1, b1, lw=1.8, ls=(0, (4, 3)))
        label(ax, e1, "E′", dx=-0.32, dy=0.25, fs=FS - 2)
        label(ax, f1, "F′", dx=0.0, dy=-0.32, fs=FS - 2)
        label(ax, b1, "B′", dx=0.0, dy=0.3, fs=FS - 2)
    frame(ax, [P(-1.6, -0.5), P(5.6, 2.5)], pad=0.2)
    return save(fig, f"cp_p_t11_{'after' if after else 'before'}.png")


def p_t12(after):
    """Theorem 12: XY parallel to BC cuts [AB] in the ratio s : t (drawn 2 : 3)."""
    fig, ax = new_axes(3.6, 3.0)
    a, b, c = P(1.4, 3.0), P(0, 0), P(3.2, 0)
    x = a + 0.4 * (b - a)
    y = a + 0.4 * (c - a)
    poly(ax, a, b, c)
    names(ax, [a, b, c], "ABC")
    if after:
        for k in (1, 3, 4):
            p, q = a + 0.2 * k * (b - a), a + 0.2 * k * (c - a)
            seg(ax, p, q, lw=1.4, ls=(0, (4, 3)))
        k1, k2 = a + 0.2 * (c - a), a + 0.0 * (c - a)
        mid = (k1 + k2) / 2
        ax.text(*(mid + P(0.3, 0.05)), r"$k$", fontsize=FS - 1, va="center")
    seg(ax, x, y)
    parallel_arrow(ax, x, y, s=0.15)
    parallel_arrow(ax, b, c, s=0.15)
    ax.text(*((a + x) / 2 + P(-0.32, 0)), r"$s$", fontsize=FS, va="center", ha="center")
    ax.text(*((x + b) / 2 + P(-0.32, 0)), r"$t$", fontsize=FS, va="center", ha="center")
    label(ax, x, "X", dx=-0.55, dy=0.0)
    label(ax, y, "Y", dx=0.32, dy=0.05)
    frame(ax, [a, b, c, P(-0.6, 0)], pad=0.45)
    return save(fig, f"cp_p_t12_{'after' if after else 'before'}.png")


def p_t13(after):
    """Theorem 13: ABC and the smaller DEF similar; X, Y with |AX| = |DE|, |AY| = |DF|."""
    fig, ax = new_axes(4.6, 2.6)
    a, b, c = P(1.2, 2.4), P(0, 0), P(2.6, 0)
    k, shift = 0.55, P(3.7, 0)
    d, e, f = (shift + k * p for p in (a, b, c))
    for tri, lets in (([a, b, c], "ABC"), ([d, e, f], "DEF")):
        poly(ax, *tri)
        names(ax, tri, lets)
        for i, n in ((0, 1), (1, 2), (2, 3)):
            for j in range(n):
                angle_mark(ax, tri[i], tri[(i + 1) % 3], tri[(i + 2) % 3], "", r=0.2 + 0.06 * j)
    if after:
        x = a + k * (b - a)
        y = a + k * (c - a)
        seg(ax, x, y, lw=2.0)
        label(ax, x, "X", dx=-0.32, dy=0.05)
        label(ax, y, "Y", dx=0.32, dy=0.05)
    frame(ax, [a, b, c, d, e, f], pad=0.45)
    return save(fig, f"cp_p_t13_{'after' if after else 'before'}.png")


def build():
    key = [k01_sss(), k02_sas(), k03_asa(), k04_rhs(), k05_ssa(), k06_aaa(), k07_kite()]
    files = {(KEY, i): name for i, name in enumerate(key, 1)}
    t11b, t11a = p_t11(False), p_t11(True)
    t12b, t12a = p_t12(False), p_t12(True)
    t13b, t13a = p_t13(False), p_t13(True)
    proof = [t11b, t11a, t11a, t12b, t12a, t12a, t13b, t13a, t13a]
    files.update({(PROOF, i): name for i, name in enumerate(proof, 1)})
    return files


if __name__ == "__main__":
    build()
