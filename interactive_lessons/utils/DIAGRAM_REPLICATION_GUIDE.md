# Diagram Replication Guide

This guide explains how to replicate math diagrams from images using Claude Code and matplotlib.

## How It Works

Claude Code is **multimodal** - it can view and analyze images. This means:
1. You show Claude Code an image of a math diagram
2. Claude Code analyzes the image and describes what it sees
3. Claude Code generates matplotlib code to recreate the diagram
4. You iterate until the diagram matches your needs

## Workflow

### Step 1: Provide the Image

Simply ask Claude Code to replicate a diagram and provide the image path:

```
"Can you replicate this diagram: /path/to/diagram.png"
```

Or if it's already in your media folder:
```
"Replicate the diagram in media/question_images/original_diagram.png"
```

### Step 2: Claude Code Analyzes

Claude Code will:
- Read and view the image
- Identify geometric shapes, labels, measurements, angles
- Determine the type of diagram (triangle, circle, graph, etc.)
- Note colors, styles, annotations

### Step 3: Code Generation

Claude Code will generate matplotlib code using the helper functions or custom code:

**For standard shapes:** Uses helper functions like `draw_triangle()`, `draw_circle()`, etc.

**For custom diagrams:** Writes custom matplotlib code with:
- `draw_polygon()` for arbitrary shapes
- `draw_angle_arc()` for angle markers
- `add_measurement_line()` for dimension annotations
- Direct matplotlib commands for complex elements

### Step 4: Iteration

If the first attempt doesn't match perfectly:
- You provide feedback ("the angle should be 45°, not 50°")
- Claude Code adjusts and regenerates
- Repeat until satisfied

## Available Helper Functions

Located in `interactive_lessons/utils/diagram_generator.py`:

### Basic Shapes
- `draw_triangle(sides, labels, angles)` - Any triangle
- `draw_right_triangle(base, height)` - Right triangles
- `draw_circle(radius, sector_angle)` - Circles and sectors
- `draw_polygon(vertices, labels)` - Any polygon

### Plotting
- `draw_coordinate_plot(functions, x_range)` - Function graphs

### Annotations
- `draw_angle_arc(ax, vertex, point1, point2)` - Angle markers
- `add_measurement_line(ax, point1, point2, label)` - Dimension lines

### Utilities
- `setup_figure(figsize, equal_aspect)` - Create figure
- `save_diagram(fig, filename, directory)` - Save to media folder

## Example: Replicating a Triangle Diagram

**User:** "Replicate this triangle diagram: media/exam_papers/question_5.png"

**Claude Code:**
1. Reads and views the image
2. Identifies: "This is a triangle ABC with sides 6cm, 8cm, 10cm, with a right angle at C"
3. Generates code:
```python
fig, ax = draw_right_triangle(6, 8, labels=('A', 'B', 'C'),
                              title='Right Triangle ABC')
path = save_diagram(fig, 'replicated_triangle.png')
```
4. Shows you the result

**User:** "The labels should be at different vertices"

**Claude Code:**
Adjusts the labels parameter and regenerates.

## Tips for Best Results

1. **Be specific:** If the original has specific measurements, colors, or styles, mention them
2. **Provide context:** "This is for a trigonometry question about the sine rule"
3. **Iterate freely:** First attempt might not be perfect - that's normal
4. **Use existing images:** Point to images already in your media folders
5. **Save variations:** Claude Code can create multiple versions with different labels/measurements

## Complex Diagrams

For complex diagrams that combine multiple elements:

**Example:** "Triangle with angle arcs, measurement lines, and shading"

Claude Code will:
- Use `draw_triangle()` as the base
- Add `draw_angle_arc()` for angle markers
- Add `add_measurement_line()` for dimensions
- Use matplotlib patches for shading

## Output

All generated diagrams are saved to:
- `media/question_images/` (default)
- `media/question_part_images/` (for question parts)
- `media/solutions/` (for solution diagrams)

You get the relative path to use in your Django models:
```
"question_images/replicated_diagram.png"
```

## Custom Matplotlib Code

For diagrams that don't fit the helper functions, Claude Code writes custom matplotlib:

```python
import matplotlib.pyplot as plt
import numpy as np

fig, ax = plt.subplots(figsize=(8, 6))

# Custom drawing commands
ax.plot([0, 5], [0, 3], 'b-', linewidth=2)
ax.add_patch(plt.Circle((2, 1), 0.5, fill=False))
# ... more custom code

save_diagram(fig, 'custom_diagram.png')
```

## Summary

**Just show Claude Code the image and ask it to replicate it!**

The multimodal capabilities mean you don't need to manually describe what's in the image - Claude Code can see it and recreate it programmatically.
