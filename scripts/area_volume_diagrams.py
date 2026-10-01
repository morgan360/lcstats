"""Draw the exam-style diagrams for the Area & Volume practice questions.

Writes PNGs to media/question_part_images/av_*.png; the add_area_volume_questions
command attaches each to its question's part (a). media/question_part_images/ is
git-ignored, so this script is the source of truth: re-run it to rebuild them.

Conventions: black line drawing on white, circles seen at an angle drawn as
ellipses, hidden edges dashed. Only dimensions the question states are labelled
-- a diagram must never print a value a later part asks for.

    python scripts/area_volume_diagrams.py
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, Polygon, Wedge

OUT = Path(__file__).resolve().parent.parent / "media" / "question_part_images"
TILT = 0.28  # ellipse height / width for a circle seen from slightly above
LW = 1.8
FS = 15

plt.rcParams["mathtext.fontset"] = "cm"


def new_axes(width, height):
    fig, ax = plt.subplots(figsize=(width, height))
    ax.set_aspect("equal")
    ax.axis("off")
    return fig, ax


def ellipse(ax, cx, cy, r, front="solid", back="dashed", lw=LW):
    """A horizontal circle of radius r seen from above: front arc then back arc."""
    t_front = np.linspace(np.pi, 2 * np.pi, 120)
    t_back = np.linspace(0, np.pi, 120)
    for t, style in ((t_front, front), (t_back, back)):
        if style is None:
            continue
        ax.plot(cx + r * np.cos(t), cy + r * TILT * np.sin(t),
                color="k", lw=lw if style == "solid" else lw * 0.8,
                ls="-" if style == "solid" else (0, (5, 4)))


def dashed(ax, p, q, lw=1.2):
    ax.plot([p[0], q[0]], [p[1], q[1]], color="k", lw=lw, ls=(0, (5, 4)))


def solid(ax, p, q, lw=LW):
    ax.plot([p[0], q[0]], [p[1], q[1]], color="k", lw=lw)


def dimension(ax, p, q, text, offset=(0, 0), ha="center", va="center"):
    """A double-headed dimension arrow from p to q, labelled at its midpoint."""
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="<->", mutation_scale=14,
                                 color="k", lw=1.1, shrinkA=0, shrinkB=0))
    mid = ((p[0] + q[0]) / 2 + offset[0], (p[1] + q[1]) / 2 + offset[1])
    ax.text(*mid, text, fontsize=FS, ha=ha, va=va,
            bbox=dict(facecolor="white", edgecolor="none", pad=1.5))


def right_angle(ax, corner, size, up=True):
    x, y = corner
    s = size
    ax.plot([x + s, x + s, x], [y, y + s, y + s], color="k", lw=1.0)


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white", pad_inches=0.15)
    plt.close(fig)
    print(f"saved {path.relative_to(OUT.parent.parent)}")


def easy2_cone():
    """Easy 2: cone r = 5, h = 12; slant height l is what (a) asks for."""
    r, h = 5, 12
    fig, ax = new_axes(4.2, 6)
    ellipse(ax, 0, 0, r)
    solid(ax, (-r, 0), (0, h))
    solid(ax, (r, 0), (0, h))
    dashed(ax, (0, 0), (0, h))
    dashed(ax, (0, 0), (r, 0))
    right_angle(ax, (0, 0), 0.7)
    ax.text(-0.35, h * 0.27, "12 cm", fontsize=FS, ha="right", va="center")
    ax.text(r / 2, -r * TILT - 0.25, "5 cm", fontsize=FS, ha="center", va="top")
    ax.text(r / 2 + 0.6, h / 2 + 0.3, r"$l$", fontsize=FS + 3, ha="left", va="center")
    ax.set_xlim(-r - 0.8, r + 1.6)
    ax.set_ylim(-r * TILT - 1.6, h + 0.6)
    save(fig, "av_easy2_cone.png")


def medium1_ornament():
    """Medium 1: cylinder r = 3, h = 10 with a hemisphere of radius 3 on top."""
    r, h = 3, 10
    fig, ax = new_axes(3.6, 6.2)
    ellipse(ax, 0, 0, r)
    solid(ax, (-r, 0), (-r, h))
    solid(ax, (r, 0), (r, h))
    # The join: its front arc is a visible seam, its back arc is hidden.
    ellipse(ax, 0, h, r)
    t = np.linspace(0, np.pi, 160)
    ax.plot(r * np.cos(t), h + r * np.sin(t), color="k", lw=LW)
    dashed(ax, (0, 0), (r, 0))
    ax.text(r / 2, -r * TILT - 0.2, "3 cm", fontsize=FS, ha="center", va="top")
    dimension(ax, (r + 1.1, 0), (r + 1.1, h), "10 cm", offset=(0.25, 0), ha="left")
    ax.set_xlim(-r - 0.6, r + 3.2)
    ax.set_ylim(-r * TILT - 1.4, h + r + 0.4)
    save(fig, "av_medium1_ornament.png")


def medium3_sector_cone():
    """Medium 3: a 216 degree sector of radius 15 folds into a cone (r, h unknown)."""
    R, angle = 15, 216
    fig, ax = new_axes(9.5, 5)
    # Sector, centred so its gap faces down.
    start = -90 + (360 - angle) / 2  # the gap is centred on straight down
    cx, cy = 0, 0
    ax.add_patch(Wedge((cx, cy), R, start, start + angle, facecolor="#eeeeee",
                       edgecolor="k", lw=LW))
    a0 = np.radians(start)
    ax.text(cx + R * 0.5 * np.cos(a0), cy + R * 0.5 * np.sin(a0) - 1.3, "15 cm",
            fontsize=FS, ha="center", va="top")
    t = np.linspace(a0, a0 + np.radians(angle), 60)
    ax.plot(cx + 2.6 * np.cos(t), cy + 2.6 * np.sin(t), color="k", lw=1.0)
    ax.text(cx - 0.6, cy + 3.4, r"$216^\circ$", fontsize=FS, ha="center", va="bottom")

    # Arrow to the cone.
    ax.add_patch(FancyArrowPatch((R + 2.5, 0), (R + 8.5, 0), arrowstyle="-|>",
                                 mutation_scale=18, color="k", lw=1.4))

    # Cone drawn to scale (r = 9, h = 12) but labelled only with letters.
    ox, r, h, l = R + 20.5, 9, 12, 15
    base_y = -h / 2
    ellipse(ax, ox, base_y, r)
    solid(ax, (ox - r, base_y), (ox, base_y + h))
    solid(ax, (ox + r, base_y), (ox, base_y + h))
    dashed(ax, (ox, base_y), (ox, base_y + h))
    dashed(ax, (ox, base_y), (ox + r, base_y))
    right_angle(ax, (ox, base_y), 0.8)
    ax.text(ox + r / 2, base_y - r * TILT - 0.3, r"$r$", fontsize=FS + 3, ha="center", va="top")
    ax.text(ox + 0.4, base_y + h * 0.45, r"$h$", fontsize=FS + 3, ha="left", va="center")
    ax.text(ox - r / 2 - 0.6, base_y + h / 2 + 0.6, "15 cm", fontsize=FS,
            ha="right", va="center")
    ax.set_xlim(-R - 1, ox + r + 1.5)
    ax.set_ylim(base_y - r * TILT - 2.2, R + 1)  # the cone base sits lowest
    save(fig, "av_medium3_sector_cone.png")


def hard1_bucket():
    """Hard 1: frustum bucket, top radius 15, base radius 10, height 12.

    The dashed lines continue the sides to the full cone's tip; its height is
    what (c) asks for, so it is not labelled.
    """
    R, r, h = 15, 10, 12
    apex_y = -24  # the sides meet 24 cm below the base
    fig, ax = new_axes(5.2, 7.4)
    ellipse(ax, 0, h, R, front="solid", back="solid")  # open top: all visible
    ellipse(ax, 0, 0, r)
    solid(ax, (-R, h), (-r, 0))
    solid(ax, (R, h), (r, 0))
    dashed(ax, (-r, 0), (0, apex_y), lw=1.0)
    dashed(ax, (r, 0), (0, apex_y), lw=1.0)
    dashed(ax, (0, h), (R, h))
    dashed(ax, (0, 0), (r, 0))
    ax.text(R / 2, h + 0.5, "15 cm", fontsize=FS, ha="center", va="bottom")
    ax.text(r * 0.35, -r * TILT - 0.3, "10 cm", fontsize=FS, ha="center", va="top")
    dimension(ax, (-R - 1.6, 0), (-R - 1.6, h), "12 cm", offset=(-0.3, 0), ha="right")
    ax.plot([-R - 2.2, -r], [0, 0], color="k", lw=0.7, ls=":")
    ax.plot([-R - 2.2, -R], [h, h], color="k", lw=0.7, ls=":")
    ax.set_xlim(-R - 6, R + 1)
    ax.set_ylim(apex_y - 1, h + R * TILT + 1.6)
    save(fig, "av_hard1_bucket.png")


def hard2_toy():
    """Hard 2: hemisphere of radius r with a cone of height 2r on its flat face."""
    r = 3
    fig, ax = new_axes(3.8, 6.2)
    t = np.linspace(np.pi, 2 * np.pi, 160)
    ax.plot(r * np.cos(t), r * np.sin(t), color="k", lw=LW)  # hemisphere outline
    ellipse(ax, 0, 0, r)  # the join: inside the toy, seam visible at the front
    solid(ax, (-r, 0), (0, 2 * r))
    solid(ax, (r, 0), (0, 2 * r))
    dashed(ax, (0, 0), (0, 2 * r))
    dashed(ax, (0, 0), (r, 0))
    right_angle(ax, (0, 0), 0.45)
    ax.text(r * 0.5, -0.06, r"$r$", fontsize=FS + 1, ha="center", va="top")
    dimension(ax, (r + 1.0, 0), (r + 1.0, 2 * r), r"$2r$", offset=(0.25, 0), ha="left")
    ax.plot([0, r + 1.3], [2 * r, 2 * r], color="k", lw=0.7, ls=":")
    ax.plot([r, r + 1.3], [0, 0], color="k", lw=0.7, ls=":")
    ax.set_xlim(-r - 0.6, r + 2.6)
    ax.set_ylim(-r - 0.6, 2 * r + 0.6)
    save(fig, "av_hard2_toy.png")


if __name__ == "__main__":
    easy2_cone()
    medium1_ornament()
    medium3_sector_cone()
    hard1_bucket()
    hard2_toy()
