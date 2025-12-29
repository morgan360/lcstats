# Diagram Generator - Usage Guide

This guide explains how to use the matplotlib-based diagram generator for creating mathematical diagrams in the LCAI Maths project.

## Overview

The diagram generator is a collection of helper functions and a workflow for creating mathematical diagrams programmatically using matplotlib. It's designed to integrate seamlessly with your Django application.

## What's Available

### Location
- **Module:** `interactive_lessons/utils/diagram_generator.py`
- **Documentation:** `interactive_lessons/utils/DIAGRAM_REPLICATION_GUIDE.md`

### Dependencies
- `matplotlib==3.9.4` (installed and in requirements.txt)
- `numpy==2.3.3` (already installed)
- Django settings integration for media paths

## Usage Methods

### Method 1: Ask Claude Code (Recommended)

Claude Code is multimodal and can see images. Simply ask for what you need:

**Examples:**
```
"Draw a triangle with sides 7, 8, 9"
"Plot y = sin(x) from 0 to 2π"
"Replicate this diagram: media/exam_papers/question_5.png"
"Create a right triangle with base 6 and height 8"
"Show a circle sector with 60° angle"
```

Claude Code will:
1. Use the appropriate helper functions
2. Generate the matplotlib code
3. Save the image to your media folder
4. Return the path for your Django models

### Method 2: Use Helper Functions Directly

Import and use the functions in your Python code:

```python
from interactive_lessons.utils.diagram_generator import (
    draw_triangle,
    draw_right_triangle,
    draw_circle,
    draw_coordinate_plot,
    draw_polygon,
    save_diagram
)

# Example: Create a triangle
fig, ax = draw_triangle(
    sides=(5, 7, 9),
    labels=('A', 'B', 'C'),
    title='Triangle ABC'
)

# Save to media folder
path = save_diagram(fig, 'my_triangle.png', directory='question_images')
# Returns: "question_images/my_triangle.png"
```

### Method 3: Django Management Command

Create a management command for batch diagram generation:

```python
# interactive_lessons/management/commands/generate_diagrams.py
from django.core.management.base import BaseCommand
from interactive_lessons.utils.diagram_generator import draw_triangle, save_diagram

class Command(BaseCommand):
    help = 'Generate mathematical diagrams'

    def handle(self, *args, **options):
        # Generate multiple diagrams
        diagrams = [
            ((3, 4, 5), 'triangle_3_4_5.png'),
            ((5, 7, 9), 'triangle_5_7_9.png'),
        ]

        for sides, filename in diagrams:
            fig, ax = draw_triangle(sides)
            path = save_diagram(fig, filename)
            self.stdout.write(f'Created: {path}')
```

Run with:
```bash
python manage.py generate_diagrams
```

## Available Functions

### Basic Shapes

#### `draw_triangle(sides, labels, angles, side_labels, angle_labels, title, figsize)`
Draw any triangle given three sides.

```python
fig, ax = draw_triangle(
    sides=(5, 7, 9),
    labels=('A', 'B', 'C'),  # Vertex labels
    side_labels=('5 cm', '7 cm', '9 cm'),  # Side labels
    angle_labels=True,  # Show calculated angles
    title='Triangle ABC'
)
```

#### `draw_right_triangle(base, height, labels, show_right_angle, title, figsize)`
Draw a right triangle with automatic hypotenuse calculation.

```python
fig, ax = draw_right_triangle(
    base=6,
    height=8,
    labels=('A', 'B', 'C'),
    show_right_angle=True,  # Show square marker
    title='Right Triangle'
)
```

#### `draw_circle(radius, center, sector_angle, show_radius, title, figsize)`
Draw a full circle or circular sector.

```python
# Full circle
fig, ax = draw_circle(radius=5, show_radius=True)

# Sector
fig, ax = draw_circle(radius=5, sector_angle=60, title='60° Sector')
```

#### `draw_polygon(vertices, labels, side_labels, angle_labels, fill, fill_color, title, figsize)`
Draw any polygon given vertex coordinates.

```python
fig, ax = draw_polygon(
    vertices=[(0, 0), (4, 0), (5, 3), (1, 4)],
    labels=['A', 'B', 'C', 'D'],
    side_labels=['4', '√10', '4', '√10'],
    fill=True,
    fill_color='lightblue'
)
```

### Plotting

#### `draw_coordinate_plot(functions, x_range, y_range, show_grid, title, xlabel, ylabel, figsize)`
Plot one or more functions on a coordinate plane.

```python
import numpy as np

fig, ax = draw_coordinate_plot(
    functions=[
        (lambda x: x**2, 'y = x²', 'blue'),
        (lambda x: np.sin(x), 'y = sin(x)', 'red')
    ],
    x_range=(-5, 5),
    y_range=(-2, 10),
    title='Functions'
)
```

### Annotation Tools

#### `draw_angle_arc(ax, vertex, point1, point2, radius, label, color)`
Add an arc to show an angle at a vertex.

```python
from interactive_lessons.utils.diagram_generator import setup_figure, draw_angle_arc

fig, ax = setup_figure()
# ... draw your shape ...
draw_angle_arc(ax, vertex=(0, 0), point1=(1, 0), point2=(0, 1),
               radius=0.5, label='90°', color='blue')
```

#### `add_measurement_line(ax, point1, point2, label, offset, color)`
Add a measurement line with arrows and label.

```python
from interactive_lessons.utils.diagram_generator import setup_figure, add_measurement_line

fig, ax = setup_figure()
# ... draw your shape ...
add_measurement_line(ax, point1=(0, 0), point2=(5, 0),
                    label='5 cm', offset=0.5)
```

### Utility Functions

#### `setup_figure(figsize, equal_aspect)`
Create a figure with standard settings.

```python
fig, ax = setup_figure(figsize=(8, 6), equal_aspect=True)
# ... add your custom matplotlib code ...
```

#### `save_diagram(fig, filename, directory)`
Save a figure to the Django media directory.

```python
path = save_diagram(fig, 'my_diagram.png', directory='question_images')
# Saves to: media/question_images/my_diagram.png
# Returns: "question_images/my_diagram.png"
```

## Image Replication Workflow

The most powerful feature is replicating diagrams from images using Claude Code's multimodal capabilities.

### How It Works

1. **Show Claude Code an image:**
   ```
   "Replicate this diagram: media/exam_papers/diagram.png"
   ```

2. **Claude Code analyzes the image:**
   - Identifies shapes (triangles, circles, polygons, etc.)
   - Reads labels, measurements, angles
   - Notes colors, styles, annotations
   - Understands the diagram structure

3. **Claude Code generates code:**
   - Uses helper functions for standard shapes
   - Writes custom matplotlib code for complex diagrams
   - Matches colors, styles, and layout

4. **Iterate if needed:**
   ```
   "The angle should be 45°, not 50°"
   "Make the triangle blue instead of black"
   "Add a label showing the hypotenuse"
   ```

### Example Workflow

```
User: "Replicate this diagram: media/question_images/triangle_abc.png"

Claude Code: [Views image, sees a right triangle with sides 3, 4, 5]

Claude Code generates:
fig, ax = draw_right_triangle(3, 4, labels=('A', 'B', 'C'))
path = save_diagram(fig, 'replicated_triangle.png')

User: "Perfect! Now make one with sides 6, 8, 10"

Claude Code:
fig, ax = draw_right_triangle(6, 8, labels=('A', 'B', 'C'))
path = save_diagram(fig, 'triangle_6_8_10.png')
```

## Output Directories

Diagrams are saved to Django media directories:

- **`media/question_images/`** - Default location for question diagrams
- **`media/question_part_images/`** - For multi-part question diagrams
- **`media/solutions/`** - For solution diagrams
- **`media/exam_papers/`** - For exam paper diagrams

Specify the directory when saving:
```python
save_diagram(fig, 'diagram.png', directory='solutions')
```

## Integration with Django Models

Use the returned path in your Django models:

```python
from interactive_lessons.utils.diagram_generator import draw_triangle, save_diagram

# Generate diagram
fig, ax = draw_triangle((5, 7, 9))
path = save_diagram(fig, 'question_123_diagram.png')

# Use in model
question_part.image = path  # "question_images/question_123_diagram.png"
question_part.save()
```

## Advanced Custom Diagrams

For complex diagrams not covered by helper functions, write custom matplotlib code:

```python
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from interactive_lessons.utils.diagram_generator import setup_figure, save_diagram

# Create custom diagram
fig, ax = setup_figure(figsize=(10, 8))

# Custom drawing
circle = patches.Circle((5, 5), 3, fill=False, edgecolor='blue', linewidth=2)
ax.add_patch(circle)

triangle_vertices = [(5, 5), (8, 5), (6.5, 7.5)]
triangle = patches.Polygon(triangle_vertices, fill=False, edgecolor='red', linewidth=2)
ax.add_patch(triangle)

ax.set_xlim(0, 10)
ax.set_ylim(0, 10)
ax.set_title('Custom Diagram', fontsize=14, fontweight='bold')

# Save
path = save_diagram(fig, 'custom_diagram.png')
```

## Tips for Best Results

1. **Use helper functions first:** They handle common cases with proper styling
2. **Leverage Claude Code:** For complex or one-off diagrams, just describe or show what you need
3. **Iterate freely:** First attempt might not be perfect - provide feedback
4. **Save variations:** Create multiple versions with different measurements/labels
5. **Consistent naming:** Use descriptive filenames like `triangle_3_4_5.png`
6. **Check media folders:** All generated diagrams are saved automatically

## Common Use Cases

### Generate Triangles for Trigonometry Questions
```python
fig, ax = draw_triangle((8, 10, 12), angle_labels=True,
                        title='Find the area')
save_diagram(fig, 'trig_question_1.png')
```

### Create Function Plots for Calculus
```python
fig, ax = draw_coordinate_plot([
    (lambda x: x**3 - 3*x, 'f(x) = x³ - 3x', 'blue')
], x_range=(-3, 3), title='Find the turning points')
save_diagram(fig, 'calculus_question_1.png')
```

### Replicate Textbook Diagrams
```
"Replicate this diagram from the textbook: ~/Downloads/textbook_page_45.png"
```

### Batch Generate Similar Diagrams
```python
for base, height in [(3, 4), (5, 12), (8, 15)]:
    fig, ax = draw_right_triangle(base, height)
    save_diagram(fig, f'right_triangle_{base}_{height}.png')
```

## Summary

**The easiest way to use this system:**

Just ask Claude Code! Say things like:
- "Draw a [shape] with [measurements]"
- "Replicate [image path]"
- "Plot [function]"
- "Create a diagram showing [concept]"

Claude Code will handle the rest, using the helper functions or writing custom code as needed.

**Everything is saved and ready to use whenever you need it!**
