"""
Diagram Generator for LCAI Maths
Helper functions to generate mathematical diagrams using matplotlib.

IMAGE REPLICATION WORKFLOW:
To replicate a diagram from an image:
1. Use the Read tool to view the image
2. Claude Code (multimodal) will analyze the image and describe what it sees
3. Use the appropriate draw_* functions or create custom matplotlib code
4. Iterate until the diagram matches the original

This module provides building blocks for common math diagrams.
For custom diagrams, Claude Code can write matplotlib code directly.
"""
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from pathlib import Path
from typing import Optional, Tuple, List, Union
import os
from django.conf import settings


def setup_figure(figsize=(8, 6), equal_aspect=True):
    """
    Create a new figure with standard settings for math diagrams.

    Args:
        figsize: Tuple of (width, height) in inches
        equal_aspect: If True, set equal aspect ratio for accurate geometric shapes

    Returns:
        fig, ax: Matplotlib figure and axes objects
    """
    fig, ax = plt.subplots(figsize=figsize)
    if equal_aspect:
        ax.set_aspect('equal')
    ax.grid(True, alpha=0.3, linestyle='--')
    return fig, ax


def save_diagram(fig, filename, directory='question_images'):
    """
    Save a matplotlib figure to the media directory.

    Args:
        fig: Matplotlib figure object
        filename: Name of the file (e.g., 'triangle_abc.png')
        directory: Subdirectory within media/ (default: 'question_images')

    Returns:
        str: Relative path to the saved file (for Django model)
    """
    media_path = Path(settings.MEDIA_ROOT) / directory
    media_path.mkdir(parents=True, exist_ok=True)

    full_path = media_path / filename
    fig.savefig(full_path, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)

    # Return relative path for Django
    return f"{directory}/{filename}"


def draw_triangle(
    sides: Tuple[float, float, float],
    labels: Optional[Tuple[str, str, str]] = None,
    side_labels: Optional[Tuple[str, str, str]] = None,
    angles: Optional[Tuple[float, float, float]] = None,
    angle_labels: Optional[bool] = True,
    title: Optional[str] = None,
    figsize: Tuple[float, float] = (8, 6)
) -> Tuple[plt.Figure, plt.Axes]:
    """
    Draw a triangle given three sides using the law of cosines to calculate angles.

    Args:
        sides: Tuple of (a, b, c) representing side lengths
        labels: Tuple of vertex labels (default: ('A', 'B', 'C'))
        side_labels: Tuple of side labels (default: uses side lengths)
        angles: Optional tuple of angles in degrees (if None, calculated from sides)
        angle_labels: If True, display angles at vertices
        title: Optional title for the diagram
        figsize: Tuple of (width, height) in inches

    Returns:
        fig, ax: Matplotlib figure and axes objects
    """
    a, b, c = sides

    # Validate triangle inequality
    if not (a + b > c and a + c > b and b + c > a):
        raise ValueError(f"Invalid triangle: sides {sides} don't satisfy triangle inequality")

    # Calculate angles using law of cosines if not provided
    if angles is None:
        # Angle A (opposite to side a)
        cos_A = (b**2 + c**2 - a**2) / (2 * b * c)
        A = np.degrees(np.arccos(np.clip(cos_A, -1, 1)))

        # Angle B (opposite to side b)
        cos_B = (a**2 + c**2 - b**2) / (2 * a * c)
        B = np.degrees(np.arccos(np.clip(cos_B, -1, 1)))

        # Angle C (opposite to side c)
        C = 180 - A - B
        angles = (A, B, C)
    else:
        A, B, C = angles

    # Place vertices
    # C at origin, B along x-axis
    vertices = np.array([
        [0, 0],           # C
        [a, 0],           # B
        [c * np.cos(np.radians(C)), c * np.sin(np.radians(C))]  # A
    ])

    # Create figure
    fig, ax = setup_figure(figsize=figsize, equal_aspect=True)

    # Draw triangle
    triangle = patches.Polygon(vertices, fill=False, edgecolor='black', linewidth=2)
    ax.add_patch(triangle)

    # Set default labels
    if labels is None:
        labels = ('A', 'B', 'C')

    if side_labels is None:
        side_labels = (f'{a}', f'{b}', f'{c}')

    # Add vertex labels
    offsets = [(0, 0.3), (0.3, 0), (-0.3, 0)]  # Offset for labels
    for i, (vertex, label, offset) in enumerate(zip(vertices, labels, offsets)):
        ax.text(vertex[0] + offset[0], vertex[1] + offset[1], label,
                fontsize=14, fontweight='bold', ha='center', va='center')

    # Add angle labels
    if angle_labels:
        angle_offset = 0.5
        ax.text(vertices[0][0] + angle_offset, vertices[0][1] + angle_offset/2,
                f'{A:.1f}°', fontsize=10, ha='center', color='blue')
        ax.text(vertices[1][0] - angle_offset, vertices[1][1] + angle_offset/2,
                f'{B:.1f}°', fontsize=10, ha='center', color='blue')
        ax.text(vertices[2][0], vertices[2][1] - angle_offset,
                f'{C:.1f}°', fontsize=10, ha='center', color='blue')

    # Add side labels (midpoints)
    midpoints = [
        (vertices[2] + vertices[1]) / 2,  # Side a (opposite A)
        (vertices[2] + vertices[0]) / 2,  # Side b (opposite B)
        (vertices[0] + vertices[1]) / 2,  # Side c (opposite C)
    ]

    side_offsets = [(0, -0.3), (0.3, 0), (0, -0.3)]
    for midpoint, side_label, offset in zip(midpoints, side_labels, side_offsets):
        ax.text(midpoint[0] + offset[0], midpoint[1] + offset[1],
                side_label, fontsize=11, ha='center', style='italic')

    # Set axis limits with padding
    all_coords = vertices
    margin = max(a, b, c) * 0.2
    ax.set_xlim(all_coords[:, 0].min() - margin, all_coords[:, 0].max() + margin)
    ax.set_ylim(all_coords[:, 1].min() - margin, all_coords[:, 1].max() + margin)

    # Remove axis ticks
    ax.set_xticks([])
    ax.set_yticks([])

    if title:
        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)

    ax.grid(False)

    return fig, ax


def draw_right_triangle(
    base: float,
    height: float,
    labels: Optional[Tuple[str, str, str]] = None,
    show_right_angle: bool = True,
    title: Optional[str] = None,
    figsize: Tuple[float, float] = (8, 6)
) -> Tuple[plt.Figure, plt.Axes]:
    """
    Draw a right triangle with given base and height.

    Args:
        base: Length of the base
        height: Length of the height
        labels: Tuple of vertex labels (default: ('A', 'B', 'C'))
        show_right_angle: If True, show right angle marker
        title: Optional title for the diagram
        figsize: Tuple of (width, height) in inches

    Returns:
        fig, ax: Matplotlib figure and axes objects
    """
    # Calculate hypotenuse
    hypotenuse = np.sqrt(base**2 + height**2)

    # Vertices: right angle at origin
    vertices = np.array([
        [0, 0],           # C (right angle)
        [base, 0],        # B
        [0, height]       # A
    ])

    fig, ax = setup_figure(figsize=figsize, equal_aspect=True)

    # Draw triangle
    triangle = patches.Polygon(vertices, fill=False, edgecolor='black', linewidth=2)
    ax.add_patch(triangle)

    # Right angle marker
    if show_right_angle:
        square_size = min(base, height) * 0.1
        right_angle = patches.Rectangle((0, 0), square_size, square_size,
                                       fill=False, edgecolor='black', linewidth=1)
        ax.add_patch(right_angle)

    # Set default labels
    if labels is None:
        labels = ('A', 'B', 'C')

    # Add vertex labels
    offsets = [(-0.3, 0.3), (0.3, -0.3), (-0.3, -0.3)]
    for vertex, label, offset in zip(vertices, labels, offsets):
        ax.text(vertex[0] + offset[0], vertex[1] + offset[1], label,
                fontsize=14, fontweight='bold', ha='center', va='center')

    # Add side labels
    ax.text(base/2, -0.5, f'{base}', fontsize=11, ha='center', style='italic')
    ax.text(-0.5, height/2, f'{height}', fontsize=11, ha='center', style='italic')
    ax.text(base/2 + 0.5, height/2, f'{hypotenuse:.2f}', fontsize=11,
            ha='center', style='italic')

    # Set axis limits
    margin = max(base, height) * 0.2
    ax.set_xlim(-margin, base + margin)
    ax.set_ylim(-margin, height + margin)

    ax.set_xticks([])
    ax.set_yticks([])

    if title:
        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)

    ax.grid(False)

    return fig, ax


def draw_circle(
    radius: float,
    center: Tuple[float, float] = (0, 0),
    sector_angle: Optional[float] = None,
    show_radius: bool = True,
    title: Optional[str] = None,
    figsize: Tuple[float, float] = (8, 8)
) -> Tuple[plt.Figure, plt.Axes]:
    """
    Draw a circle or circular sector.

    Args:
        radius: Circle radius
        center: Center coordinates (x, y)
        sector_angle: If provided, draw a sector with this angle in degrees
        show_radius: If True, draw radius line
        title: Optional title for the diagram
        figsize: Tuple of (width, height) in inches

    Returns:
        fig, ax: Matplotlib figure and axes objects
    """
    fig, ax = setup_figure(figsize=figsize, equal_aspect=True)

    if sector_angle is None:
        # Full circle
        circle = patches.Circle(center, radius, fill=False, edgecolor='black', linewidth=2)
        ax.add_patch(circle)

        if show_radius:
            ax.plot([center[0], center[0] + radius], [center[1], center[1]],
                   'b-', linewidth=1.5, label=f'r = {radius}')
            ax.plot(center[0], center[1], 'ko', markersize=5)
            ax.legend()
    else:
        # Sector
        theta = np.linspace(0, np.radians(sector_angle), 100)
        x = center[0] + radius * np.cos(theta)
        y = center[1] + radius * np.sin(theta)

        # Draw arc
        ax.plot(x, y, 'b-', linewidth=2)

        # Draw radii
        ax.plot([center[0], x[0]], [center[1], y[0]], 'b-', linewidth=2)
        ax.plot([center[0], x[-1]], [center[1], y[-1]], 'b-', linewidth=2)

        # Center point
        ax.plot(center[0], center[1], 'ko', markersize=5)

        # Angle annotation
        ax.text(center[0] + radius * 0.3, center[1] + radius * 0.1,
               f'{sector_angle}°', fontsize=12, color='blue')

    # Set axis limits
    margin = radius * 0.3
    ax.set_xlim(center[0] - radius - margin, center[0] + radius + margin)
    ax.set_ylim(center[1] - radius - margin, center[1] + radius + margin)

    ax.set_xticks([])
    ax.set_yticks([])

    if title:
        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)

    ax.grid(False)

    return fig, ax


def draw_coordinate_plot(
    functions: List[Tuple[callable, str, str]],
    x_range: Tuple[float, float] = (-10, 10),
    y_range: Optional[Tuple[float, float]] = None,
    show_grid: bool = True,
    title: Optional[str] = None,
    xlabel: str = 'x',
    ylabel: str = 'y',
    figsize: Tuple[float, float] = (10, 6)
) -> Tuple[plt.Figure, plt.Axes]:
    """
    Draw one or more functions on a coordinate plane.

    Args:
        functions: List of (function, label, color) tuples
        x_range: Tuple of (x_min, x_max)
        y_range: Optional tuple of (y_min, y_max)
        show_grid: If True, show grid
        title: Optional title for the diagram
        xlabel: Label for x-axis
        ylabel: Label for y-axis
        figsize: Tuple of (width, height) in inches

    Returns:
        fig, ax: Matplotlib figure and axes objects

    Example:
        fig, ax = draw_coordinate_plot([
            (lambda x: x**2, 'y = x²', 'blue'),
            (lambda x: 2*x + 1, 'y = 2x + 1', 'red')
        ])
    """
    fig, ax = plt.subplots(figsize=figsize)

    x = np.linspace(x_range[0], x_range[1], 500)

    for func, label, color in functions:
        try:
            y = func(x)
            ax.plot(x, y, label=label, color=color, linewidth=2)
        except Exception as e:
            print(f"Warning: Could not plot {label}: {e}")

    # Draw axes
    ax.axhline(y=0, color='black', linewidth=0.8)
    ax.axvline(x=0, color='black', linewidth=0.8)

    if show_grid:
        ax.grid(True, alpha=0.3, linestyle='--')

    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)

    if y_range:
        ax.set_ylim(y_range)

    if len(functions) > 0:
        ax.legend(fontsize=11)

    if title:
        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)

    return fig, ax


def draw_polygon(
    vertices: List[Tuple[float, float]],
    labels: Optional[List[str]] = None,
    side_labels: Optional[List[str]] = None,
    angle_labels: Optional[List[str]] = None,
    fill: bool = False,
    fill_color: str = 'lightblue',
    title: Optional[str] = None,
    figsize: Tuple[float, float] = (8, 6)
) -> Tuple[plt.Figure, plt.Axes]:
    """
    Draw any polygon given vertices.

    Args:
        vertices: List of (x, y) coordinates for vertices
        labels: List of vertex labels
        side_labels: List of labels for each side
        angle_labels: List of angle labels at each vertex
        fill: If True, fill the polygon
        fill_color: Color for fill
        title: Optional title
        figsize: Tuple of (width, height) in inches

    Returns:
        fig, ax: Matplotlib figure and axes objects
    """
    vertices_array = np.array(vertices)

    fig, ax = setup_figure(figsize=figsize, equal_aspect=True)

    # Draw polygon
    polygon = patches.Polygon(vertices_array, fill=fill,
                             facecolor=fill_color if fill else None,
                             edgecolor='black', linewidth=2, alpha=0.6)
    ax.add_patch(polygon)

    # Add vertex labels
    if labels:
        for i, (vertex, label) in enumerate(zip(vertices_array, labels)):
            # Calculate offset direction (away from polygon center)
            center = vertices_array.mean(axis=0)
            direction = vertex - center
            direction = direction / np.linalg.norm(direction) * 0.4
            ax.text(vertex[0] + direction[0], vertex[1] + direction[1], label,
                   fontsize=14, fontweight='bold', ha='center', va='center')

    # Add side labels
    if side_labels:
        for i in range(len(vertices_array)):
            v1 = vertices_array[i]
            v2 = vertices_array[(i + 1) % len(vertices_array)]
            midpoint = (v1 + v2) / 2

            # Perpendicular offset
            direction = v2 - v1
            perp = np.array([-direction[1], direction[0]])
            perp = perp / np.linalg.norm(perp) * 0.3

            if i < len(side_labels):
                ax.text(midpoint[0] + perp[0], midpoint[1] + perp[1],
                       side_labels[i], fontsize=11, ha='center', style='italic')

    # Add angle labels
    if angle_labels:
        for i, label in enumerate(angle_labels):
            if i < len(vertices_array):
                vertex = vertices_array[i]
                center = vertices_array.mean(axis=0)
                direction = vertex - center
                direction = direction / np.linalg.norm(direction) * 0.6
                ax.text(vertex[0] - direction[0] * 0.5, vertex[1] - direction[1] * 0.5,
                       label, fontsize=10, ha='center', color='blue')

    # Set axis limits
    margin = max(vertices_array.max(axis=0) - vertices_array.min(axis=0)) * 0.2
    ax.set_xlim(vertices_array[:, 0].min() - margin, vertices_array[:, 0].max() + margin)
    ax.set_ylim(vertices_array[:, 1].min() - margin, vertices_array[:, 1].max() + margin)

    ax.set_xticks([])
    ax.set_yticks([])
    ax.grid(False)

    if title:
        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)

    return fig, ax


def draw_angle_arc(
    ax: plt.Axes,
    vertex: Tuple[float, float],
    point1: Tuple[float, float],
    point2: Tuple[float, float],
    radius: float = 0.5,
    label: Optional[str] = None,
    color: str = 'blue'
):
    """
    Draw an arc to represent an angle at a vertex between two points.

    Args:
        ax: Matplotlib axes object
        vertex: The vertex point (x, y)
        point1: First point defining the angle
        point2: Second point defining the angle
        radius: Radius of the arc
        label: Optional label for the angle
        color: Color of the arc
    """
    v = np.array(vertex)
    p1 = np.array(point1)
    p2 = np.array(point2)

    # Calculate angles
    angle1 = np.degrees(np.arctan2(p1[1] - v[1], p1[0] - v[0]))
    angle2 = np.degrees(np.arctan2(p2[1] - v[1], p2[0] - v[0]))

    # Ensure angle1 < angle2
    if angle1 > angle2:
        angle1, angle2 = angle2, angle1

    # Draw arc
    arc = patches.Arc(v, 2*radius, 2*radius, angle=0,
                     theta1=angle1, theta2=angle2, color=color, linewidth=2)
    ax.add_patch(arc)

    # Add label
    if label:
        mid_angle = np.radians((angle1 + angle2) / 2)
        label_pos = v + (radius * 0.7) * np.array([np.cos(mid_angle), np.sin(mid_angle)])
        ax.text(label_pos[0], label_pos[1], label, fontsize=10,
               ha='center', va='center', color=color)


def add_measurement_line(
    ax: plt.Axes,
    point1: Tuple[float, float],
    point2: Tuple[float, float],
    label: str,
    offset: float = 0.3,
    color: str = 'black'
):
    """
    Add a measurement line with arrows and label between two points.

    Args:
        ax: Matplotlib axes object
        point1: Start point (x, y)
        point2: End point (x, y)
        label: Measurement label
        offset: Offset distance from the line
        color: Color of the measurement line
    """
    p1 = np.array(point1)
    p2 = np.array(point2)

    # Calculate perpendicular offset
    direction = p2 - p1
    length = np.linalg.norm(direction)
    perp = np.array([-direction[1], direction[0]])
    perp = perp / np.linalg.norm(perp) * offset

    # Offset points
    p1_offset = p1 + perp
    p2_offset = p2 + perp

    # Draw line with arrows
    ax.annotate('', xy=p2_offset, xytext=p1_offset,
               arrowprops=dict(arrowstyle='<->', color=color, lw=1.5))

    # Add label
    midpoint = (p1_offset + p2_offset) / 2
    ax.text(midpoint[0], midpoint[1], label, fontsize=10,
           ha='center', va='center', color=color,
           bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='none'))


# Quick usage examples
if __name__ == "__main__":
    # Example 1: Triangle with sides 5, 7, 9
    fig, ax = draw_triangle((5, 7, 9), title="Triangle ABC")
    save_diagram(fig, "example_triangle.png")

    # Example 2: Right triangle
    fig, ax = draw_right_triangle(3, 4, title="Right Triangle")
    save_diagram(fig, "example_right_triangle.png")

    # Example 3: Circle with sector
    fig, ax = draw_circle(5, sector_angle=60, title="Circle Sector (60°)")
    save_diagram(fig, "example_circle_sector.png")

    # Example 4: Coordinate plot
    fig, ax = draw_coordinate_plot([
        (lambda x: x**2, 'y = x²', 'blue'),
        (lambda x: 2*x + 1, 'y = 2x + 1', 'red')
    ], title="Functions Plot")
    save_diagram(fig, "example_functions.png")

    print("Example diagrams created successfully!")
