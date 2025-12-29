# Manim MCP Server Setup Guide

This guide explains how to set up and use the Manim MCP server for creating mathematical animations through Claude Code.

## What is Manim MCP?

The Manim MCP server is a Model Context Protocol server that allows Claude Code to generate mathematical animations using Manim (Mathematical Animation Engine). Instead of manually writing Manim code, you can describe animations in natural language and Claude will generate them for you!

## Installation Status

✅ **Manim Community Edition** - Installed (version 0.19.1)
✅ **MCP Python Package** - Installed (version 1.22.0)
✅ **Manim MCP Server** - Cloned to `/Users/morgan/manim-mcp-server/`

## Configuration for Claude Desktop

To enable the Manim MCP server in Claude Desktop, you need to update your Claude Desktop configuration file.

### Step 1: Locate Configuration File

The configuration file is located at:
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

### Step 2: Update Configuration

Add this configuration to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "manim-server": {
      "command": "/Users/morgan/lcstats/.venv/bin/python3",
      "args": ["/Users/morgan/manim-mcp-server/src/manim_server.py"],
      "env": {
        "MANIM_EXECUTABLE": "/Users/morgan/lcstats/.venv/bin/manim"
      }
    }
  }
}
```

**Note**: If you already have other MCP servers configured, merge this entry into your existing `mcpServers` object.

### Step 3: Restart Claude Desktop

After updating the configuration:
1. Quit Claude Desktop completely
2. Relaunch Claude Desktop
3. The Manim MCP server will now be available

## How to Use

Once configured, you can ask Claude Code to create Manim animations using natural language:

### Example Requests

**Basic Geometric Animations:**
```
"Create a Manim animation showing a square transforming into a circle"
"Animate a triangle rotating 360 degrees"
"Show how to construct a perpendicular bisector"
```

**Mathematical Concepts:**
```
"Animate the sine wave from 0 to 2π"
"Create an animation explaining the Pythagoras theorem"
"Show how limits work as x approaches infinity"
```

**Function Visualizations:**
```
"Animate the graph of f(x) = x² and show its derivative"
"Visualize the area under a curve for integration"
"Show the transformation of y = sin(x) to y = 2sin(3x)"
```

**3Blue1Brown Style:**
```
"Create an animation showing matrix multiplication visually"
"Animate a transformation in linear algebra"
"Show the concept of eigenvectors and eigenvalues"
```

## Output

Animations are rendered as MP4 videos and saved to the Manim media directory (typically `~/manim-mcp-server/media/videos/`).

Claude Code will:
1. Generate the Manim Python script
2. Execute the script using the MCP server
3. Return the path to the generated video
4. You can then move/copy the video to your Django media folder if needed

## Features

The Manim MCP server supports:
- **2D and 3D animations** - Geometric shapes, graphs, transformations
- **Text and LaTeX** - Mathematical equations and labels
- **Color and styling** - Custom colors, gradients, animations styles
- **Complex scenes** - Multiple objects, sequential animations, transitions
- **Educational content** - Perfect for creating math tutorial videos

## Advantages Over matplotlib

**Manim** is better for:
- **Animated** mathematical explanations
- Videos for teaching/tutorials
- Complex transformations and morphing
- 3Blue1Brown-style educational content
- Time-based mathematical concepts

**matplotlib** (our existing setup) is better for:
- **Static** diagrams
- Quick on-demand images
- Simple geometric shapes
- Embedding in Django question images
- Instant generation without rendering time

## Workflow Comparison

### Using Manim MCP:
```
User: "Create an animation showing how sin(x) changes as x goes from 0 to 2π"
Claude Code: [Generates Manim script via MCP]
Manim: [Renders video - takes 10-60 seconds]
Result: MP4 video file
```

### Using matplotlib (existing):
```
User: "Draw a graph of sin(x) from 0 to 2π"
Claude Code: [Generates matplotlib code]
matplotlib: [Creates image - instant]
Result: PNG image file saved to media/question_images/
```

## When to Use Each

**Use Manim MCP for:**
- Creating tutorial/explanation videos
- Animated problem walkthroughs
- Complex mathematical demonstrations
- Content for YouTube/video lessons
- Showing processes and transformations

**Use matplotlib for:**
- Static question diagrams
- Exam paper illustrations
- Quick reference images
- Embedding in web pages
- Instant diagram generation

## Troubleshooting

### Server Not Appearing in Claude Desktop

1. Check the configuration file path is correct
2. Ensure JSON syntax is valid (no trailing commas)
3. Verify all paths are absolute (not relative)
4. Restart Claude Desktop completely

### Manim Errors

If animations fail to render:
1. Test Manim directly: `manim --version`
2. Check the Manim executable path: `which manim`
3. Verify Python can find Manim: `python -c "import manim; print(manim.__version__)"`

### Permission Issues

If you get permission errors:
```bash
chmod +x /Users/morgan/manim-mcp-server/src/manim_server.py
```

## Advanced Usage

### Custom Manim Configuration

You can customize Manim's output settings by creating a `manim.cfg` file in your project:

```ini
[CLI]
quality = high_quality
format = mp4
save_last_frame = True
write_to_movie = True

[output]
media_dir = /Users/morgan/lcstats/media/animations/
```

### Moving Animations to Django Media

After generating an animation:

```bash
# Copy from Manim output to Django media
cp ~/manim-mcp-server/media/videos/480p15/MyScene.mp4 \
   /Users/morgan/lcstats/media/animations/
```

Or ask Claude Code to do it for you after generating the animation!

## Example: Full Workflow

**Step 1:** Ask Claude Code
```
"Create a Manim animation showing how to find the area of a triangle
using the formula A = ½bh, with base 6 and height 4"
```

**Step 2:** Claude Code generates Manim script
```python
from manim import *

class TriangleArea(Scene):
    def construct(self):
        # Create triangle
        triangle = Polygon([0,0,0], [6,0,0], [0,4,0])
        triangle.set_fill(BLUE, opacity=0.3)
        triangle.set_stroke(BLUE, width=3)

        # Add labels
        base = Text("b = 6").next_to(triangle, DOWN)
        height = Line([0,0,0], [0,4,0]).set_color(RED)
        height_label = Text("h = 4").next_to(height, LEFT)

        # Formula
        formula = MathTex(r"A = \frac{1}{2}bh")
        formula.to_edge(UP)

        # Animate
        self.play(Create(triangle))
        self.play(Write(base), Create(height), Write(height_label))
        self.play(Write(formula))

        # Calculate
        calc = MathTex(r"A = \frac{1}{2}(6)(4) = 12")
        calc.next_to(formula, DOWN)
        self.play(Transform(formula.copy(), calc))
        self.wait(2)
```

**Step 3:** MCP server renders the animation
- Generates MP4 video
- Returns path to Claude Code

**Step 4:** Use the video
- Upload to Django media
- Embed in lessons
- Share with students

## Resources

- **Manim Documentation**: https://docs.manim.community/
- **Manim Examples**: https://docs.manim.community/en/stable/examples.html
- **3Blue1Brown**: https://www.3blue1brown.com/ (Manim creator)
- **MCP Documentation**: https://modelcontextprotocol.io/

## Summary

You now have **two powerful tools** for mathematical visualization:

1. **matplotlib** (via diagram_generator.py) - Fast static diagrams
2. **Manim** (via MCP server) - Beautiful animated explanations

Use them together to create comprehensive educational content for your LCAI Maths platform!

**Next Step:** Configure Claude Desktop with the settings above, then start creating animations by simply describing what you want!
