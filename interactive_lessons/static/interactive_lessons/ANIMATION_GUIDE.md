# Math Animation System - Integration Guide

This guide explains how to add animated visualizations to your math questions.

## Files Created

1. **binomial-animation.js** - Basketball free throw animation for binomial distribution
2. **animations.css** - Reusable CSS animations for all math topics
3. **animation_demo.html** - Demo page showing the animation in action

## Quick Start

### View the Demo

Visit: `/interactive/demo/animation/`

This shows the basketball binomial distribution animation with all three scenarios.

## How to Add Animations to Existing Questions

### Step 1: Add CSS and JS to Your Template

In your Django template (e.g., `quiz.html`), add these lines in the `<head>` section:

```html
{% load static %}

<!-- Animation CSS -->
<link rel="stylesheet" href="{% static 'interactive_lessons/animations.css' %}">
```

And before the closing `</body>` tag:

```html
<!-- Animation JavaScript -->
<script src="{% static 'interactive_lessons/binomial-animation.js' %}"></script>
```

### Step 2: Add Animation Container to Your Question

Where you want the animation to appear (e.g., in the hint section or above the question):

```html
<div class="math-animation-container">
    <div id="basketball-animation"></div>
</div>

<div class="animation-controls">
    <button class="animation-btn animation-btn-primary" onclick="runAnimation()">
        ▶ Play Animation
    </button>
    <button class="animation-btn animation-btn-secondary" onclick="animation.reset()">
        Reset
    </button>
</div>
```

### Step 3: Initialize the Animation

Add this JavaScript:

```html
<script>
    // Initialize the basketball animation
    let animation = new BasketballAnimation('basketball-animation', {
        width: 800,
        height: 400,
        throwDuration: 1000,
        pauseBetweenThrows: 600
    });

    // Run animation function
    async function runAnimation() {
        animation.reset();
        await animation.animateSequence(
            [true, true, true, true, false], // Sequence: 4 makes, 1 miss
            {
                part: 'i',
                description: 'Misses for the 1st time on his 5th free throw',
                p: 0.8,
                q: 0.2,
                steps: [
                    'No. of Trials: n = 5',
                    'p = 0.8 and q = 1 – 0.8 = 0.2',
                    'r = 4 (number of successes)',
                    'P(4) = (0.8)⁴(0.2)¹ = 0.08192'
                ],
                answer: 'P(misses on 5th) = 0.08192 or 8.192%'
            }
        );
    }
</script>
```

## Customizing the Animation

### Animation Options

```javascript
new BasketballAnimation('container-id', {
    width: 800,              // Canvas width in pixels
    height: 400,             // Canvas height in pixels
    throwDuration: 1000,     // Duration of each throw (ms)
    pauseBetweenThrows: 600, // Pause between throws (ms)
    showSteps: true          // Show calculation steps
});
```

### Creating Custom Sequences

The `sequence` array uses:
- `true` = successful throw (makes basket)
- `false` = failed throw (misses)

Examples:
```javascript
// All makes
[true, true, true, true, true]

// All misses
[false, false, false, false]

// Alternating
[true, false, true, false, true]

// First success on 3rd try
[false, false, true]
```

## Conditional Display in Django Templates

Show animations only for specific questions:

```html
{% if question.section == "Binomial Distribution" %}
    <div class="math-animation-container">
        <div id="basketball-animation"></div>
    </div>

    <script>
        // Initialize animation for binomial questions
        let animation = new BasketballAnimation('basketball-animation');

        // Auto-play on page load (optional)
        window.addEventListener('load', () => {
            runAnimation();
        });
    </script>
{% endif %}
```

## Creating New Animation Types

The system is designed to be extensible. To create animations for other topics:

### 1. Create a New Animation Class

Follow the pattern in `binomial-animation.js`:

```javascript
class CalculusAnimation {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        // ... initialization
    }

    async animateDerivative(functionData) {
        // Your animation logic
    }
}
```

### 2. Use the Shared CSS

The `animations.css` file provides reusable animations:

- `@keyframes slideIn` - Slide in from left
- `@keyframes fadeIn` - Fade in
- `@keyframes scaleIn` - Scale up
- `@keyframes pulse` - Pulsing effect
- `@keyframes highlight` - Background highlight
- `@keyframes bounce` - Bouncing motion

Apply them like this:

```css
.my-element {
    animation: slideIn 0.5s ease;
}
```

## Topics That Could Benefit from Animation

### Already Implemented
- ✅ **Binomial Distribution** - Basketball free throws

### Easy to Implement
- **Probability Trees** - Branching diagrams
- **Venn Diagrams** - Set operations
- **Dice/Coin Flips** - Random events
- **Normal Distribution** - Bell curve with shaded areas

### Medium Complexity
- **Calculus** - Derivative slopes, tangent lines, area under curves
- **Trigonometry** - Unit circle, wave functions
- **Functions** - Graph transformations, domain/range
- **Sequences** - Arithmetic/geometric progressions

### Advanced
- **3D Geometry** - Rotating shapes (would need Three.js)
- **Complex Numbers** - Argand diagrams
- **Differential Equations** - Slope fields

## Integration with Existing Quiz Flow

### Show Animation in Hints

```html
<details class="hint-section">
    <summary>💡 Hint (with animation)</summary>

    <div id="hint-animation"></div>

    <script>
        // Initialize when hint is opened
        document.querySelector('.hint-section').addEventListener('toggle', (e) => {
            if (e.target.open) {
                let hintAnim = new BasketballAnimation('hint-animation', {
                    width: 600,
                    height: 300
                });
                // Play animation
            }
        });
    </script>
</details>
```

### Show Animation with Solution

```html
<button onclick="showSolution()">Show Solution</button>

<div id="solution-section" style="display: none;">
    <div id="solution-animation"></div>
    <!-- Solution text -->
</div>

<script>
    function showSolution() {
        document.getElementById('solution-section').style.display = 'block';

        // Initialize and play animation
        let solAnim = new BasketballAnimation('solution-animation');
        solAnim.animateSequence(/* ... */);
    }
</script>
```

## Performance Considerations

1. **Lazy Loading** - Only initialize animations when needed (e.g., when user clicks button)
2. **Single Instance** - Reuse animation objects instead of creating new ones
3. **Canvas Cleanup** - Call `reset()` before replaying to clear previous drawings
4. **Mobile Responsive** - Canvas automatically scales based on container width

## Browser Compatibility

- ✅ Chrome/Edge (latest)
- ✅ Firefox (latest)
- ✅ Safari (latest)
- ✅ Mobile browsers (iOS Safari, Chrome Mobile)

**No external dependencies** except KaTeX (already in use).

## Accessibility

The CSS includes:

```css
@media (prefers-reduced-motion: reduce) {
    /* Animations disabled for users with motion sensitivity */
}
```

Always provide text alternatives:
- Show the same information in text below the animation
- Provide "Skip Animation" button
- Don't rely solely on animation to convey information

## Next Steps

1. **Try the demo**: Visit `/interactive/demo/animation/`
2. **Test integration**: Add to one question in quiz.html
3. **Create more animations**: Adapt the basketball pattern for other topics
4. **Get feedback**: Test with students to see what's helpful

## Need Help?

Check these files:
- `binomial-animation.js` - Full basketball implementation
- `animation_demo.html` - Complete working example
- `animations.css` - All available CSS animations

The basketball example is fully commented and can serve as a template for other animation types.
