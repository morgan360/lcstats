# Manim Animation Specifications

## Standard Requirements for All Animations

### Footer and Branding
- **Copyright Footer**: Always include "© Rosary College 2025" in the bottom right corner throughout the entire video
- **Closing Screen**: Every animation must end with a closing screen displaying:
  - "Rosary College"
  - "2025"
- **Pause Before Exit**: Pause after filling the screen before performing any wipe/exit animation

### Layout Guidelines
- **Avoid Bottom Screen Area**: Do not place content/text at the bottom of the screen (reserve for footer)
- **Safe Area**: Keep main content in the upper 80-85% of the screen

### Output Configuration
- **Output Directory**: `/Users/morgan/lcstats/media/quickkicks`
- **File Naming**: Use descriptive names related to the mathematical concept being illustrated

## Text Positioning Guidelines for Manim

### Core Principles
1. **Avoid single VGroup.arrange() for complex layouts** with titles and content
2. **Separate content into distinct VGroups** (e.g., title, description, questions)
3. **Use .next_to() with generous buff values** (0.6-1.0) between major sections
4. **For line spacing within paragraphs**, use buff=0.3-0.35 minimum
5. **Position elements explicitly relative to:**
   - Screen edges: `.to_edge(UP, buff=0.8)` or `.to_edge(UP, buff=1.0)`
   - Other elements: `element.next_to(previous_element, DOWN, buff=0.8)`
6. **Test critical scenes**: if titles are at UP buff=0.8, content should start at least buff=0.8 below
7. **Never use ORIGIN or centered positioning** for multi-line text without explicit shift values

### Recommended Pattern

```python
# GOOD PATTERN: Explicit positioning with generous buffers
title = Text("Title", font_size=36, color=YELLOW).to_edge(UP, buff=0.8)

content_group = VGroup(
    Text("Line 1", font_size=28),
    Text("Line 2", font_size=28)
).arrange(DOWN, buff=0.35, aligned_edge=LEFT)
content_group.next_to(title, DOWN, buff=0.8)

formula = MathTex(r"formula", font_size=42)
formula.next_to(content_group, DOWN, buff=1.0)
```

### Anti-Pattern to Avoid

```python
# BAD PATTERN: Too little control, insufficient spacing
everything = VGroup(
    title, line1, line2, formula
).arrange(DOWN, buff=0.25)  # Too little control!
```

## CLI Usage

### Basic Command Structure
```bash
manim -pql <scene_file.py> <SceneName>
```

### Quality Options
- `-ql` - Low quality (480p, fast render)
- `-qm` - Medium quality (720p)
- `-qh` - High quality (1080p)
- `-qk` - 4K quality (2160p)

### Common Flags
- `-p` - Preview after rendering
- `-s` - Save last frame as image
- `-a` - Render all scenes in file
- `--format=gif` - Output as GIF instead of video

### Example Commands
```bash
# Render single scene, low quality, with preview
manim -pql standard_deviation_animation.py StandardDeviationScene

# Render high quality without preview
manim -qh standard_deviation_animation.py StandardDeviationScene

# Output directory is automatically set to /Users/morgan/lcstats/media/quickkicks
# via manim.cfg or command line flag
```

## Adding Background Music

### Automated Music Addition

After rendering your animation, use the `add_music_to_manim.py` script to automatically add background music:

```bash
# Add music to the latest rendered video
python add_music_to_manim.py --latest

# Add music to a specific video file
python add_music_to_manim.py path/to/video.mp4

# Use custom music file
python add_music_to_manim.py video.mp4 path/to/music.mp3

# Adjust volume (0.0 to 1.0, default is 0.3)
python add_music_to_manim.py video.mp4 music.mp3 0.5

# Process latest video for a specific scene
python add_music_to_manim.py --latest --scene MySceneName
```

### Default Settings
- **Default Music File**: `/Users/morgan/lcstats/media/quickkicks/just-relax.mp3`
- **Default Volume**: 0.3 (30% of original music volume)
- **Output Format**: Creates `<original_name>_with_music.mp4` in the same directory

### Manual FFmpeg Command (if needed)
```bash
ffmpeg -i video.mp4 -i music.mp3 -c:v copy -c:a aac \
  -map 0:v:0 -map 1:a:0 -shortest -filter:a "volume=0.3" \
  output_with_music.mp4
```

### Workflow
1. Render your animation: `manim -pql my_animation.py MyScene`
2. Add music: `python add_music_to_manim.py --latest`
3. The script automatically finds the latest video and adds music
4. Output video saved with `_with_music` suffix

## Template Structure

### Recommended Scene Template
```python
from manim import *

class MyMathScene(Scene):
    def construct(self):
        # Add copyright footer (persistent throughout)
        footer = Text("© Rosary College 2025", font_size=16)
        footer.to_corner(DR, buff=0.3)
        self.add(footer)

        # Main animation content here
        # Example with proper positioning:
        title = Text("Concept Title", font_size=36, color=YELLOW)
        title.to_edge(UP, buff=0.8)

        content = VGroup(
            Text("Description line 1", font_size=28),
            Text("Description line 2", font_size=28)
        ).arrange(DOWN, buff=0.35, aligned_edge=LEFT)
        content.next_to(title, DOWN, buff=0.8)

        self.play(Write(title))
        self.wait(0.5)
        self.play(FadeIn(content))
        self.wait(2)

        # Pause before closing
        self.wait(1)

        # Closing screen
        self.show_closing_screen()

    def show_closing_screen(self):
        # Clear main content (keep footer)
        self.play(*[FadeOut(mob) for mob in self.mobjects[1:]])

        # Show college name and year
        college_name = Text("Rosary College", font_size=48)
        year = Text("2025", font_size=36)
        closing_group = VGroup(college_name, year).arrange(DOWN, buff=0.5)

        self.play(FadeIn(closing_group))
        self.wait(2)
        self.play(FadeOut(closing_group))
```

## Notes
- All animations should follow these specifications unless explicitly stated otherwise
- Footer should remain visible and legible throughout the animation
- Closing screen should be professional and clean
- Test renders with `-ql` flag before final high-quality renders
- Always use explicit positioning with generous buffers to avoid text overlap
- Reserve bottom 15-20% of screen for footer area