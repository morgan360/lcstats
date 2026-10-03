"""Draw the diagrams for the Geometry-Theorems practice questions.

Writes PNGs to media/question_part_images/geo_*.png; the
add_geometry_theorems_questions command attaches each to its question's part (a).
media/question_part_images/ is git-ignored, so this script is the source of
truth: re-run it to rebuild them.

Every figure is placed from the question's own angles and lengths, so it is
drawn to scale (lengths up to an overall factor). Only what the question states
is labelled -- a diagram must never print a value a part asks for, and must not
mark a right angle that a part asks the student to establish.

    python scripts/geometry_theorem_diagrams.py
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle

OUT = Path(__file__).resolve().parent.parent / "media" / "question_part_images"
LW = 1.8
FS = 15

plt.rcParams["mathtext.fontset"] = "cm"


def new_axes(width, height):
    fig, ax = plt.subplots(figsize=(width, height))
    ax.set_aspect("equal")
    ax.axis("off")
    return fig, ax


def P(x, y):
    return np.array([x, y], dtype=float)


def polar(r, degrees, centre=(0, 0)):
    t = np.radians(degrees)
    return P(centre[0] + r * np.cos(t), centre[1] + r * np.sin(t))


def seg(ax, p, q, lw=LW, ls="-"):
    ax.plot([p[0], q[0]], [p[1], q[1]], color="k", lw=lw, ls=ls,
            solid_capstyle="round")


def poly(ax, *pts):
    for p, q in zip(pts, pts[1:] + pts[:1]):
        seg(ax, p, q)


def dot(ax, p):
    ax.plot(*p, "o", color="k", ms=4)


def point_label(ax, p, text, away_from, dist=0.32):
    """Letter at p, pushed out along the direction from away_from to p."""
    d = p - away_from
    d = d / np.linalg.norm(d)
    ax.text(*(p + dist * d), text, fontsize=FS + 1, ha="center", va="center",
            style="italic")


def angle_mark(ax, v, p, q, text, r=0.45, text_r=None, fs=FS, text_deg=None):
    """Arc for the angle pvq (the one under 180 degrees), labelled on its bisector."""
    a1 = np.degrees(np.arctan2(*(p - v)[::-1]))
    a2 = np.degrees(np.arctan2(*(q - v)[::-1]))
    sweep = (a2 - a1) % 360
    if sweep > 180:
        a1, a2, sweep = a2, a1, 360 - sweep
    t = np.radians(np.linspace(a1, a1 + sweep, 60))
    ax.plot(v[0] + r * np.cos(t), v[1] + r * np.sin(t), color="k", lw=1.0)
    mid = np.radians(a1 + sweep / 2 if text_deg is None else text_deg)
    tr = text_r if text_r is not None else r + 0.38
    ax.text(v[0] + tr * np.cos(mid), v[1] + tr * np.sin(mid), text, fontsize=fs,
            ha="center", va="center")


def right_angle(ax, v, p, q, s=0.25):
    u = (p - v) / np.linalg.norm(p - v) * s
    w = (q - v) / np.linalg.norm(q - v) * s
    ax.plot(*np.array([v + u, v + u + w, v + w]).T, color="k", lw=1.0)


def tick(ax, p, q, n=1, s=0.13):
    """n equal-length ticks across the middle of segment pq."""
    d = (q - p) / np.linalg.norm(q - p)
    nrm = P(-d[1], d[0])
    mid = (p + q) / 2
    for k in range(n):
        c = mid + (k - (n - 1) / 2) * 0.09 * d
        seg(ax, c - s * nrm, c + s * nrm, lw=1.2)


def parallel_arrow(ax, p, q, n=1, at=0.5, s=0.16):
    """n arrowheads on segment pq, pointing from p to q."""
    d = (q - p) / np.linalg.norm(q - p)
    nrm = P(-d[1], d[0])
    for k in range(n):
        tip = p + at * (q - p) + k * 0.14 * d
        for side in (1, -1):
            seg(ax, tip, tip - s * d + side * 0.7 * s * nrm, lw=1.3)


def length_label(ax, p, q, text, away, dist=0.3, at=0.5):
    """Label beside segment pq, on the side away from the point ``away``."""
    d = (q - p) / np.linalg.norm(q - p)
    nrm = P(-d[1], d[0])
    spot = p + at * (q - p)
    if np.dot(spot - away, nrm) < 0:
        nrm = -nrm
    ax.text(*(spot + dist * nrm), text, fontsize=FS, ha="center", va="center")


def frame(ax, pts, pad=0.7):
    pts = np.array(pts)
    ax.set_xlim(pts[:, 0].min() - pad, pts[:, 0].max() + pad)
    ax.set_ylim(pts[:, 1].min() - pad, pts[:, 1].max() + pad)


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white", pad_inches=0.15)
    plt.close(fig)
    print(f"saved {path.relative_to(OUT.parent.parent)}")


def easy1_crossing_lines():
    """Easy 1: two lines cross at 70/110 degrees; 3x+10 and 5x-30 are opposite."""
    o = P(0, 0)
    a, b = 15, 85  # directions of the two lines; 85 - 15 = 70
    ends = [polar(2.4, a), polar(2.4, a + 180), polar(2.4, b), polar(2.4, b + 180)]
    fig, ax = new_axes(5, 5)
    seg(ax, ends[0], ends[1])
    seg(ax, ends[2], ends[3])
    angle_mark(ax, o, ends[0], ends[2], r"$(3x+10)^\circ$", r=0.5, text_r=1.25)
    angle_mark(ax, o, ends[1], ends[3], r"$(5x-30)^\circ$", r=0.5, text_r=1.25)
    angle_mark(ax, o, ends[2], ends[1], r"$y^\circ$", r=0.3, text_r=0.75)
    frame(ax, ends, pad=0.3)
    save(fig, "geo_easy1_crossing_lines.png")


def easy2_isosceles():
    """Easy 2: |AB| = |AC|, apex 42 degrees, [BC] extended to D."""
    b, c = P(0, 0), P(2, 0)
    a = P(1, np.tan(np.radians(69)))
    d = P(3.4, 0)
    fig, ax = new_axes(5, 4.5)
    poly(ax, a, b, c)
    seg(ax, c, d)
    tick(ax, a, b)
    tick(ax, a, c)
    angle_mark(ax, a, b, c, r"$42^\circ$", r=0.45, text_r=0.85)
    centre = (a + b + c) / 3
    for p, name in ((a, "A"), (b, "B"), (c, "C")):
        point_label(ax, p, name, centre)
    ax.text(*(d + P(0, -0.3)), "D", fontsize=FS + 1, ha="center", style="italic")
    frame(ax, [a, b, d], pad=0.5)
    save(fig, "geo_easy2_isosceles.png")


def easy3_parallel_lines():
    """Easy 3: l parallel to m; 65 at P below l right of the transversal."""
    p = P(1, 1.6)
    q = p + 1.6 / np.sin(np.radians(65)) * P(np.cos(np.radians(-65)), np.sin(np.radians(-65)))
    fig, ax = new_axes(6, 4)
    l0, l1 = P(-1.5, p[1]), P(4, p[1])
    m0, m1 = P(-1.5, 0), P(4, 0)
    seg(ax, l0, l1)
    seg(ax, m0, m1)
    parallel_arrow(ax, l0, l1, at=0.85)
    parallel_arrow(ax, m0, m1, at=0.85)
    ax.text(*(l1 + P(0.25, 0)), r"$l$", fontsize=FS + 2, va="center")
    ax.text(*(m1 + P(0.25, 0)), r"$m$", fontsize=FS + 2, va="center")
    d = (q - p) / np.linalg.norm(q - p)
    t0, t1 = p - 0.9 * d, q + 0.9 * d
    seg(ax, t0, t1)
    angle_mark(ax, p, l1, q, r"$65^\circ$", r=0.4, text_r=0.85)
    angle_mark(ax, q, m0, p, r"$a$", r=0.28, text_r=0.6)
    angle_mark(ax, q, m1, p, r"$b$", r=0.45, text_r=0.75)
    ax.text(*(p + P(-0.4, 0.3)), "P", fontsize=FS + 1, style="italic", ha="center")
    ax.text(*(q + P(0.3, -0.3)), "Q", fontsize=FS + 1, style="italic", ha="center")
    frame(ax, [l0, l1, m0, m1, t0, t1], pad=0.4)
    save(fig, "geo_easy3_parallel_lines.png")


def easy4_exterior_angle():
    """Easy 4: angles x (=42) at A and 2x (=84) at B; exterior 126 at C."""
    k = 4
    b = P(0, 0)
    c = P(k * np.sin(np.radians(42)), 0)
    a = b + k * np.sin(np.radians(54)) * P(np.cos(np.radians(84)), np.sin(np.radians(84)))
    d = c + P(1.5, 0)
    fig, ax = new_axes(5, 5)
    poly(ax, a, b, c)
    seg(ax, c, d)
    angle_mark(ax, a, b, c, r"$x^\circ$", r=0.5, text_r=0.85)
    angle_mark(ax, b, c, a, r"$2x^\circ$", r=0.35, text_r=0.75)
    angle_mark(ax, c, a, d, r"$126^\circ$", r=0.35, text_r=0.8)
    centre = (a + b + c) / 3
    for p, name in ((a, "A"), (b, "B"), (c, "C")):
        point_label(ax, p, name, centre)
    ax.text(*(d + P(0, -0.3)), "D", fontsize=FS + 1, ha="center", style="italic")
    frame(ax, [a, b, d], pad=0.5)
    save(fig, "geo_easy4_exterior_angle.png")


def medium1_parallelogram():
    """Medium 1: parallelogram ABCD, angle A = 85, diagonals meet at E."""
    a, b = P(0, 0), P(4, 0)
    d = polar(2.6, 85)
    c = b + d
    e = (a + c) / 2
    fig, ax = new_axes(6, 4)
    poly(ax, a, b, c, d)
    seg(ax, a, c, lw=1.2)
    seg(ax, b, d, lw=1.2)
    parallel_arrow(ax, a, b)
    parallel_arrow(ax, d, c)
    parallel_arrow(ax, a, d, n=2)
    parallel_arrow(ax, b, c, n=2)
    angle_mark(ax, a, b, d, r"$(3y-20)^\circ$", r=0.35, text_r=1.3, text_deg=50, fs=FS - 2)
    angle_mark(ax, c, d, b, r"$(2y+15)^\circ$", r=0.35, text_r=1.3, text_deg=230, fs=FS - 2)
    for p, name in ((a, "A"), (b, "B"), (c, "C"), (d, "D")):
        point_label(ax, p, name, e)
    ax.text(*(e + P(0, -0.35)), "E", fontsize=FS + 1, ha="center", style="italic")
    frame(ax, [a, b, c, d], pad=0.6)
    save(fig, "geo_medium1_parallelogram.png")


def medium2_parallel_in_triangle():
    """Medium 2: XY parallel to BC; |AX| = 6, |XB| = 4, |AY| = 9, |XY| = 9."""
    a, b, c = P(1.6, 4.2), P(0, 0), P(5.2, 0)
    x = a + 0.6 * (b - a)
    y = a + 0.6 * (c - a)
    fig, ax = new_axes(5.5, 5)
    poly(ax, a, b, c)
    seg(ax, x, y)
    parallel_arrow(ax, x, y)
    parallel_arrow(ax, b, c)
    centre = (a + b + c) / 3
    length_label(ax, a, x, "6", centre)
    length_label(ax, x, b, "4", centre)
    length_label(ax, a, y, "9", centre)
    length_label(ax, x, y, "9", c, dist=0.25)
    centre = (a + b + c) / 3
    for p, name in ((a, "A"), (b, "B"), (c, "C")):
        point_label(ax, p, name, centre)
    ax.text(*(x + P(-0.3, 0)), "X", fontsize=FS + 1, ha="center", va="center", style="italic")
    ax.text(*(y + P(0.3, 0)), "Y", fontsize=FS + 1, ha="center", va="center", style="italic")
    frame(ax, [a, b, c], pad=0.5)
    save(fig, "geo_medium2_parallel_in_triangle.png")


def medium3_bow_tie():
    """Medium 3: AE and BD cross at C, AB parallel to DE; |CA| 4, |CB| 5, |AB| 6, |CE| 10."""
    s = 0.55
    angle_c = np.degrees(np.arccos((4 ** 2 + 5 ** 2 - 6 ** 2) / (2 * 4 * 5)))
    c = P(0, 0)
    a = polar(4 * s, 165)
    b = polar(5 * s, 165 - angle_c)
    e = -2.5 * a
    d = -2.5 * b
    fig, ax = new_axes(7, 6)
    poly(ax, a, b, c)
    poly(ax, c, d, e)
    parallel_arrow(ax, a, b, at=0.75)
    parallel_arrow(ax, e, d)
    length_label(ax, c, a, "4", b)
    length_label(ax, c, b, "5", a)
    length_label(ax, a, b, "6", c)
    length_label(ax, c, e, "10", d, dist=0.35)
    for p, name in ((a, "A"), (b, "B"), (d, "D"), (e, "E")):
        point_label(ax, p, name, c)
    ax.text(*(c + polar(0.42, 35)), "C", fontsize=FS + 1, ha="center", style="italic")
    frame(ax, [a, b, d, e], pad=0.5)
    save(fig, "geo_medium3_bow_tie.png")


def medium4_quadrilateral():
    """Medium 4: |AB| 7, |BC| 24, |AC| 25; angle ACD = 90, |CD| = 60."""
    s = 0.16
    b = P(0, 0)
    a = P(0, 7 * s)
    c = P(24 * s, 0)
    ac = c - a
    perp = P(-ac[1], ac[0]) / np.linalg.norm(ac)  # points away from B
    d = c + 60 * s * perp
    fig, ax = new_axes(6, 8)
    poly(ax, a, b, c, d)
    seg(ax, a, c)
    right_angle(ax, c, a, d, s=0.3)
    length_label(ax, a, b, "7", c)
    length_label(ax, b, c, "24", a)
    length_label(ax, a, c, "25", b, at=0.4)
    length_label(ax, c, d, "60", a, dist=0.4)
    centre = (a + b + c + d) / 4
    for p, name in ((a, "A"), (b, "B"), (c, "C"), (d, "D")):
        point_label(ax, p, name, centre)
    frame(ax, [a, b, c, d], pad=0.6)
    save(fig, "geo_medium4_quadrilateral.png")


def circle_base(ax, o, r=2):
    ax.add_patch(Circle(o, r, fill=False, edgecolor="k", lw=LW))
    dot(ax, o)


def hard1_centre_angle():
    """Hard 1: angle ACB = 38 at the circumference; O the centre."""
    o, r = P(0, 0), 2
    a, b, c = polar(r, 232), polar(r, 308), polar(r, 90)
    fig, ax = new_axes(5, 5)
    circle_base(ax, o, r)
    seg(ax, c, a)
    seg(ax, c, b)
    seg(ax, o, a)
    seg(ax, o, b)
    seg(ax, a, b)
    angle_mark(ax, c, a, b, r"$38^\circ$", r=0.55, text_r=0.95)
    for p, name in ((a, "A"), (b, "B"), (c, "C")):
        point_label(ax, p, name, o)
    ax.text(*(o + P(0.3, 0.1)), "O", fontsize=FS + 1, ha="center", style="italic")
    frame(ax, [P(-r, -r), P(r, r)], pad=0.5)
    save(fig, "geo_hard1_centre_angle.png")


def hard2_two_isosceles():
    """Hard 2: angle OCA = 25, angle OCB = 30; A, B, C on the circle, O the centre."""
    o, r = P(0, 0), 2
    a, b, c = polar(r, 220), polar(r, 330), polar(r, 90)
    fig, ax = new_axes(5, 5)
    circle_base(ax, o, r)
    seg(ax, c, a)
    seg(ax, c, b)
    seg(ax, o, a)
    seg(ax, o, b)
    seg(ax, o, c)
    angle_mark(ax, c, a, o, r"$25^\circ$", r=0.6, text_r=1.0, fs=FS - 2)
    angle_mark(ax, c, o, b, r"$30^\circ$", r=0.6, text_r=1.0, fs=FS - 2)
    for p, name in ((a, "A"), (b, "B"), (c, "C")):
        point_label(ax, p, name, o)
    ax.text(*(o + P(0.1, -0.35)), "O", fontsize=FS + 1, ha="center", style="italic")
    frame(ax, [P(-r, -r), P(r, r)], pad=0.5)
    save(fig, "geo_hard2_two_isosceles.png")


def hard3_parallelogram_area():
    """Hard 3: |AB| = 12, |AD| = 7.5, perpendicular height to AB = 5."""
    s = 0.4
    a, b = P(0, 0), P(12 * s, 0)
    d = P(np.sqrt(7.5 ** 2 - 5 ** 2) * s, 5 * s)
    c = b + d
    foot = P(d[0], 0)
    fig, ax = new_axes(6.5, 3.5)
    poly(ax, a, b, c, d)
    seg(ax, d, foot, lw=1.2, ls=(0, (5, 4)))
    right_angle(ax, foot, b, d, s=0.2)
    length_label(ax, a, b, "12", d, at=0.72)
    length_label(ax, a, d, "7.5", b, dist=0.4)
    ax.text(*((d + foot) / 2 + P(0.25, 0)), "5", fontsize=FS, va="center")
    centre = (a + b + c + d) / 4
    for p, name in ((a, "A"), (b, "B"), (c, "C"), (d, "D")):
        point_label(ax, p, name, centre)
    frame(ax, [a, b, c, d], pad=0.6)
    save(fig, "geo_hard3_parallelogram_area.png")


if __name__ == "__main__":
    easy1_crossing_lines()
    easy2_isosceles()
    easy3_parallel_lines()
    easy4_exterior_angle()
    medium1_parallelogram()
    medium2_parallel_in_triangle()
    medium3_bow_tie()
    medium4_quadrilateral()
    hard1_centre_angle()
    hard2_two_isosceles()
    hard3_parallelogram_area()
