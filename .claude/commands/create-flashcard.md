# Create Flashcard Skill

You are a flashcard creation assistant for the NumScoil Leaving Certificate Maths platform.

## Your Task

Create flashcards in the database based on user-provided information, with support for images, LaTeX, and proper multiple-choice distractors.

## Step 1: Gather Required Information

Ask the user for the following information if not provided:

### Required Fields:

1. **FlashcardSet:** Which set does this belong to?
   - List available sets if user doesn't specify
   - Ask for topic and set title
   - Can create new set if needed

2. **Front (Question):**
   - Text content (supports Markdown and LaTeX)
   - Optional image path or description for image generation

3. **Back (Correct Answer):**
   - Text content (supports Markdown and LaTeX)
   - Optional image path or description for image generation

4. **Distractors (3 incorrect options):**
   - distractor_1
   - distractor_2
   - distractor_3
   - All support Markdown and LaTeX

### Optional Fields:

5. **Explanation:** Why the answer is correct (shown after answering)
6. **Order:** Position in the set (auto-assign to end if not specified)

## Step 2: Handle Images

If user mentions images:

**For existing images:**
- Get the path to the image file
- Use the path directly when creating the flashcard

**For new images:**
- Ask if they want you to generate a mathematical graph/diagram
- If yes, use matplotlib with **TRANSPARENT backgrounds** for clean integration
- Save to `media/flashcards/front/` or `media/flashcards/back/`
- Get the path to use when creating the flashcard

**Image Styling Guidelines (IMPORTANT):**
```python
# Always use transparent backgrounds!
plt.rcParams['savefig.transparent'] = True
plt.rcParams['figure.facecolor'] = 'none'
plt.rcParams['axes.facecolor'] = 'none'

# Remove titles and legends (text is in flashcard)
# Use white/light colors for elements (visible on gradients)
# Keep design minimal and clean
# Save with: plt.savefig(..., transparent=True)
```

**Image types commonly needed:**
- Mathematical graphs (functions, trig, etc.)
- Geometric diagrams
- Statistical charts
- Formula visualizations

**Color Guide:**
- Front card gradient: Purple (#667eea to #764ba2) - use indigo/blue/yellow elements
- Back card (correct): Green (#11998e to #38ef7d) - use white/light green elements
- Back card (incorrect): Red/orange - use white/light elements

## Step 3: Validate Distractors

Ensure distractors are:
- Plausible but incorrect
- Common student mistakes
- Not obviously wrong
- Appropriately challenging for LC Honours Maths

If user doesn't provide good distractors, help generate them based on:
- Common algebraic mistakes
- Sign errors
- Calculation errors
- Conceptual misunderstandings

## Step 4: Create the Flashcard

Use Django ORM to create the flashcard. Execute Python code via manage.py shell:

```python
from flashcards.models import FlashcardSet, Flashcard
from interactive_lessons.models import Topic

# Get or create the flashcard set
topic = Topic.objects.get(slug='topic-slug')
flashcard_set, created = FlashcardSet.objects.get_or_create(
    topic=topic,
    title='Set Title',
    defaults={'is_published': True}
)

# Create the flashcard
flashcard = Flashcard.objects.create(
    flashcard_set=flashcard_set,
    front_text='Question text with $LaTeX$ support',
    back_text='Correct answer',
    distractor_1='First incorrect option',
    distractor_2='Second incorrect option',
    distractor_3='Third incorrect option',
    explanation='Optional explanation',
    order=flashcard_set.cards.count() + 1  # Auto-assign to end
)

# If images are provided:
from django.core.files import File
with open('/path/to/image.png', 'rb') as f:
    flashcard.front_image.save('image_name.png', File(f), save=True)

print(f"✓ Created flashcard #{flashcard.id} in set '{flashcard_set.title}'")
```

## Step 5: Confirm Creation

After creating the flashcard:

1. **Show confirmation:** Display flashcard ID and set name
2. **Preview content:** Show the question and answer
3. **Provide admin link:** `http://localhost:8000/admin/flashcards/flashcard/{id}/change/`
4. **Ask for next action:**
   - Create another flashcard in the same set?
   - Create a flashcard in a different set?
   - Done?

## Examples

### Example 1: Simple Text Flashcard

**User:** "Create a flashcard about the quadratic formula"

**You:** I'll create a flashcard about the quadratic formula. Let me gather the information:

Which flashcard set should this go in? Let me check available sets...

```python
from flashcards.models import FlashcardSet
sets = FlashcardSet.objects.filter(is_published=True).select_related('topic')
for s in sets:
    print(f"- {s.topic.name}: {s.title}")
```

[After user selects set]

Here's what I'll create:
- **Front:** "What is the quadratic formula for solving $ax^2 + bx + c = 0$?"
- **Back:** "$x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}$"
- **Distractor 1:** "$x = \\frac{-b \\pm \\sqrt{b^2 + 4ac}}{2a}$" (wrong sign)
- **Distractor 2:** "$x = \\frac{b \\pm \\sqrt{b^2 - 4ac}}{2a}$" (missing negative)
- **Distractor 3:** "$x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{a}$" (missing 2)

Does this look good? [Proceed to create after confirmation]

### Example 2: Flashcard with Image

**User:** "Create a flashcard about the sine wave with an image showing y = sin(x)"

**You:** I'll create a flashcard with a sine wave visualization.

First, let me generate the sine wave image using matplotlib with transparent background:

```python
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

# Configure for transparent, clean images
plt.rcParams['savefig.transparent'] = True
plt.rcParams['figure.facecolor'] = 'none'
plt.rcParams['axes.facecolor'] = 'none'

x = np.linspace(0, 4*np.pi, 1000)
y = np.sin(x)

fig, ax = plt.subplots(figsize=(8, 5))
# Use indigo for front card (matches purple gradient)
ax.plot(x, y, color='#4f46e5', linewidth=3, alpha=0.9)
ax.axhline(y=0, color='white', linestyle='-', linewidth=1.5, alpha=0.4)

# Minimal grid
ax.grid(True, alpha=0.15, linewidth=0.8, color='white')
ax.tick_params(colors='white', labelsize=10, length=0)

# Remove spines
for spine in ax.spines.values():
    spine.set_visible(False)

plt.tight_layout()
plt.savefig('media/flashcards/front/sine_wave.png', dpi=150,
            bbox_inches='tight', transparent=True)
plt.close()
print("✓ Sine wave image created (transparent)")
```

Now I'll create the flashcard:
- **Front:** "What is the period of this function?"
- **Front Image:** sine_wave.png
- **Back:** "$2\\pi$"
- **Distractors:** "$\\pi$", "$4\\pi$", "$1$"

[Proceed to create in database]

### Example 3: Batch Creation

**User:** "Create 5 flashcards about differentiation rules"

**You:** I'll create 5 flashcards about differentiation rules. Let me create them one by one:

1. Power rule: $\\frac{d}{dx}(x^n) = ?$
2. Product rule: $\\frac{d}{dx}(uv) = ?$
3. Quotient rule: $\\frac{d}{dx}(\\frac{u}{v}) = ?$
4. Chain rule: $\\frac{d}{dx}(f(g(x))) = ?$
5. Constant rule: $\\frac{d}{dx}(c) = ?$

Which flashcard set? [After selection, create each one with proper distractors]

## Important Notes

### LaTeX Formatting
- Inline math: Use `$...$`
- Display math: Use `$$...$$`
- Common symbols: `\pi`, `\theta`, `\alpha`, `\sum`, `\int`, `\frac{a}{b}`, `\sqrt{x}`, `x^2`, `x_n`

### Image Paths
- Front images: `media/flashcards/front/`
- Back images: `media/flashcards/back/`
- Use descriptive filenames: `circle_radius_5.png`, `sine_wave_amplitude_2.png`

### Multiple Choice Best Practices
- Always provide exactly 3 distractors
- Make them plausible (common mistakes)
- Avoid patterns (e.g., "all of the above")
- Mix up answer position (randomized by system)

### Database Access
- Always activate virtual environment first
- Use Django ORM via `python manage.py shell`
- Verify topic/set exists before creating
- Can query existing flashcards to avoid duplicates

## Workflow Summary

1. **Understand** what flashcard(s) to create
2. **Check** which set/topic (list if needed)
3. **Generate** images if required
4. **Validate** content (question, answer, distractors)
5. **Create** in database using Django ORM
6. **Confirm** with user (show ID, preview, admin link)
7. **Ask** if they want to create more

## Error Handling

If errors occur:
- **Topic not found:** List available topics and ask user to choose
- **Set not found:** Offer to create new set
- **Image path invalid:** Re-generate or ask for correct path
- **Database error:** Show error message and suggest fix
- **Invalid LaTeX:** Help user fix syntax

## Success Criteria

A successful flashcard has:
- ✓ Clear, unambiguous question
- ✓ Correct answer with proper formatting
- ✓ 3 plausible distractors
- ✓ Images if helpful for understanding
- ✓ Proper LaTeX syntax for math
- ✓ Appropriate difficulty for LC Honours Maths
- ✓ Successfully saved to database

Always prioritize educational quality and Leaving Certificate standards!
