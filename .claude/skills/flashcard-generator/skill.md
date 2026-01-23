# Flashcard Generator Skill

This skill helps create flashcards for the NumScoil flashcard system by generating multiple-choice questions with AI assistance.

## Overview

Generate flashcards from text, questions, or images using Claude AI. The skill creates flashcards directly in your local database, which you can then export using `python manage.py export_flashcards` for import on the live site.

## How It Works

1. **User provides input**: Text statement, question, or image
2. **AI generates flashcard**: Creates question, correct answer, 3 distractors, and explanation
3. **User reviews and confirms**: Preview the flashcard before saving
4. **Save to database**: Creates FlashcardSet (if needed) and Flashcard records
5. **Repeat or export**: Continue adding cards or export the set

## Flashcard Structure

Each flashcard must have:
- **Front**: Question text (supports LaTeX with `$...$` or `$$...$$`)
- **Back**: Correct answer text
- **Distractors**: 3 incorrect options for multiple choice
- **Explanation**: Detailed explanation of why the answer is correct
- **Optional**: `front_image` and/or `back_image` (stored in `media/flashcards/`)

## Input Types

### Text/Question Input
User provides a statement or question, and AI generates:
- Multiple-choice question based on the concept
- One correct answer
- Three plausible distractors
- Explanation with reasoning

### Image Input
User provides an image (diagram, graph, formula), and AI:
- Analyzes the image content
- Generates relevant question
- Creates answer options
- Provides explanation
- Optionally attaches image to front or back of card

## Workflow

### Initial Setup
1. Ask user for topic/set name
2. Check if `FlashcardSet` exists for this topic
3. If not, create new set linked to appropriate `Topic` from `interactive_lessons`

### Card Generation Loop
For each flashcard:

1. **Get Input**
   - Prompt: "Provide a statement, question, or image for the flashcard"
   - If image: Use Read tool to analyze it
   - If text: Process directly

2. **Generate Flashcard Content**
   - Use Claude AI to create:
     - Question (front)
     - Correct answer (back)
     - 3 distractors (distractor_1, distractor_2, distractor_3)
     - Explanation
   - Ensure LaTeX formatting is preserved with proper delimiters

3. **Preview for User**
   - Display generated content in readable format
   - Show all options shuffled (as students would see)
   - Ask: "Accept this flashcard? (yes/no/edit/skip)"

4. **Handle User Response**
   - **yes**: Save to database
   - **no**: Regenerate with different approach
   - **edit**: Allow manual field editing
   - **skip**: Move to next card

5. **Save to Database**
   ```python
   from flashcards.models import Flashcard, FlashcardSet

   flashcard = Flashcard.objects.create(
       flashcard_set=flashcard_set,
       front="Question text with $LaTeX$ if needed",
       back="Correct answer",
       distractor_1="Wrong option 1",
       distractor_2="Wrong option 2",
       distractor_3="Wrong option 3",
       explanation="Detailed explanation...",
       front_image=None,  # or path to uploaded image
       back_image=None
   )
   ```

6. **Continue or Finish**
   - Ask: "Add another flashcard to this set? (yes/no)"
   - If no: Provide export instructions

### Completion
When user is done:
```bash
# Show command to export the set
python manage.py export_flashcards --topic "Topic Name"
```

## AI Generation Guidelines

### Question Quality
- **Clear and unambiguous**: Question should have one definitively correct answer
- **Appropriate difficulty**: Match the LC Higher Level Maths standard
- **Conceptual focus**: Test understanding, not just memorization
- **LaTeX formatting**: Use `$...$` for inline math, `$$...$$` for display math

### Distractor Quality
- **Plausible**: Should be tempting to students who don't fully understand
- **Common mistakes**: Based on typical student errors
- **Not obviously wrong**: Avoid distractors that are clearly incorrect
- **Varied**: Don't make all distractors similar patterns

### Explanation Quality
- **Why it's correct**: Explain the correct answer reasoning
- **Why others are wrong**: Briefly mention why distractors are incorrect
- **Teaching moment**: Use as opportunity to reinforce the concept
- **Concise but complete**: 2-4 sentences typically sufficient

### LaTeX Handling
- Preserve mathematical notation exactly
- Common patterns:
  - Fractions: `$\frac{a}{b}$`
  - Square roots: `$\sqrt{x}$`
  - Exponents: `$x^2$`
  - Greek letters: `$\mu$`, `$\sigma$`
  - Equations: `$$y = mx + c$$`

## Image Handling

### When Image is Front
- Question references the image: "In the diagram above, what is..."
- Save image to `media/flashcards/set_name/front_image_N.png`
- Set `front_image` field to the file path

### When Image is Back
- Image is part of explanation (diagram, worked solution)
- Save to `media/flashcards/set_name/back_image_N.png`
- Set `back_image` field to the file path

### Image Storage
```python
from django.core.files.base import ContentFile
import os

# Create directory if needed
os.makedirs('media/flashcards/set_name', exist_ok=True)

# Save image
flashcard.front_image.save(
    'front_image_1.png',
    ContentFile(image_data),
    save=False
)
flashcard.save()
```

## Database Models Reference

```python
# flashcards/models.py

class FlashcardSet(models.Model):
    topic = models.ForeignKey('interactive_lessons.Topic', on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Flashcard(models.Model):
    flashcard_set = models.ForeignKey(FlashcardSet, on_delete=models.CASCADE)
    front = models.TextField()  # Question text
    back = models.TextField()   # Correct answer
    distractor_1 = models.CharField(max_length=500)
    distractor_2 = models.CharField(max_length=500)
    distractor_3 = models.CharField(max_length=500)
    explanation = models.TextField()
    front_image = models.ImageField(upload_to='flashcards/', blank=True, null=True)
    back_image = models.ImageField(upload_to='flashcards/', blank=True, null=True)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
```

## Step-by-Step Implementation

### Step 1: Setup and Topic Selection
```python
# Ask user for topic/set information
topic_name = input("Enter topic name (e.g., 'Probability'): ")
set_name = input("Enter flashcard set name (e.g., 'Conditional Probability'): ")

# Find or create Topic
from interactive_lessons.models import Topic
try:
    topic = Topic.objects.get(name__iexact=topic_name)
except Topic.DoesNotExist:
    print(f"Topic '{topic_name}' not found. Available topics:")
    for t in Topic.objects.all():
        print(f"  - {t.name}")
    # Let user select from list

# Find or create FlashcardSet
from flashcards.models import FlashcardSet
flashcard_set, created = FlashcardSet.objects.get_or_create(
    topic=topic,
    name=set_name,
    defaults={'description': f'Flashcards for {set_name}'}
)
```

### Step 2: Generate Flashcard with AI
```python
# Prepare prompt for Claude
prompt = f"""
Generate a multiple-choice flashcard for LC Higher Level Maths on the topic: {topic_name}

Based on this input: {user_input}

Create:
1. A clear, specific question (front of card)
2. The correct answer (back of card)
3. Three plausible but incorrect distractors
4. A detailed explanation (2-4 sentences)

Requirements:
- Use LaTeX notation with $ delimiters for math (e.g., $x^2$, $\\frac{{a}}{{b}}$)
- Distractors should represent common student mistakes
- Explanation should teach why the answer is correct

Return as JSON:
{{
  "front": "Question text with $LaTeX$",
  "back": "Correct answer",
  "distractor_1": "Wrong option 1",
  "distractor_2": "Wrong option 2",
  "distractor_3": "Wrong option 3",
  "explanation": "Why this is correct..."
}}
"""

# Call AI (similar pattern to extract-questions)
# Parse JSON response
```

### Step 3: Preview and Confirm
```python
print("\n" + "="*60)
print("GENERATED FLASHCARD PREVIEW")
print("="*60)
print(f"\nQuestion: {flashcard_data['front']}")
print(f"\nOptions (shuffled for display):")
options = [
    flashcard_data['back'],
    flashcard_data['distractor_1'],
    flashcard_data['distractor_2'],
    flashcard_data['distractor_3']
]
import random
random.shuffle(options)
for i, opt in enumerate(options, 1):
    marker = "✓" if opt == flashcard_data['back'] else " "
    print(f"  {i}. {opt} {marker}")

print(f"\nExplanation: {flashcard_data['explanation']}")
print("="*60)

response = input("\nAccept this flashcard? (yes/no/edit/skip): ").lower()
```

### Step 4: Save to Database
```python
if response == 'yes':
    from flashcards.models import Flashcard

    # Get next order number
    max_order = Flashcard.objects.filter(
        flashcard_set=flashcard_set
    ).aggregate(models.Max('order'))['order__max'] or 0

    flashcard = Flashcard.objects.create(
        flashcard_set=flashcard_set,
        front=flashcard_data['front'],
        back=flashcard_data['back'],
        distractor_1=flashcard_data['distractor_1'],
        distractor_2=flashcard_data['distractor_2'],
        distractor_3=flashcard_data['distractor_3'],
        explanation=flashcard_data['explanation'],
        order=max_order + 1
    )

    print(f"✓ Flashcard saved! (ID: {flashcard.id})")

elif response == 'edit':
    # Allow manual editing of fields
    flashcard_data['front'] = input(f"Question [{flashcard_data['front']}]: ") or flashcard_data['front']
    # ... edit other fields
    # Then save
```

## Important Notes

### LaTeX Sanitization
- The flashcard model does NOT auto-sanitize LaTeX like Question models
- Ensure proper delimiters: `$...$` for inline, `$$...$$` for display
- Frontend renders using markdown-katex extension

### Mastery States
- New flashcards start in "new" state
- Student progression: new → learning → know → retired
- Don't set initial state - let the system handle it

### Export/Import Workflow
```bash
# After creating flashcards locally:
python manage.py export_flashcards --topic "Probability"

# This creates: flashcards_export_probability_YYYYMMDD.json

# Transfer JSON to live site, then:
python manage.py import_flashcards flashcards_export_probability_YYYYMMDD.json
```

### Validation
Before saving, validate:
- All required fields are non-empty
- Distractors are different from correct answer
- Distractors are different from each other
- LaTeX syntax is valid (check matching delimiters)

## Error Handling

### AI Generation Fails
- Retry with simplified prompt
- Fall back to manual entry mode
- Log the error for debugging

### Duplicate Detection
```python
# Check if similar flashcard exists
existing = Flashcard.objects.filter(
    flashcard_set=flashcard_set,
    front__icontains=key_phrase
)
if existing.exists():
    print(f"Warning: Similar flashcard may exist (ID: {existing.first().id})")
    # Ask user if they want to continue
```

### Image Upload Errors
```python
try:
    # Save image
    flashcard.front_image.save(filename, content)
except Exception as e:
    print(f"Error saving image: {e}")
    # Ask if user wants to continue without image
```

## Best Practices

1. **Batch by topic**: Create full sets at once for consistency
2. **Review before export**: Test flashcards locally before live import
3. **Consistent naming**: Use clear, descriptive set names
4. **Order matters**: Cards are displayed in `order` field sequence
5. **Quality over quantity**: Better to have 10 great cards than 50 mediocre ones

## Example Session

```
User: /flashcard-generator

Claude: I'll help you create flashcards for NumScoil. Let me start by getting some information.

What topic would you like to create flashcards for?

Available topics:
  - Probability
  - Statistics
  - Algebra
  - Differentiation
  - Integration
  (etc.)

User: Probability

Claude: Great! What should we name this flashcard set? (e.g., "Conditional Probability", "Bayes Theorem")

User: Conditional Probability Basics

Claude: Perfect! I've found the Probability topic and created/found the flashcard set "Conditional Probability Basics".

Now, let's create flashcards. You can provide:
- A statement or concept
- A question you want to turn into a flashcard
- An image path for diagram-based questions

What would you like to create a flashcard about? (or type 'done' to finish)

User: The probability of A and B occurring is P(A and B) = P(A) × P(B|A)

Claude: [Generates flashcard using AI]

============================================================
GENERATED FLASHCARD PREVIEW
============================================================

Question: What is the formula for the probability of two events A and B both occurring?

Options (shuffled for display):
  1. $P(A \text{ and } B) = P(A) + P(B)$
  2. $P(A \text{ and } B) = P(A) \times P(B|A)$ ✓
  3. $P(A \text{ and } B) = P(A) \times P(B)$
  4. $P(A \text{ and } B) = P(B) \times P(A|B)$

Explanation: The formula $P(A \text{ and } B) = P(A) \times P(B|A)$ represents the multiplication rule for dependent events. P(B|A) is the probability of B occurring given that A has already occurred. This differs from independent events where we would simply multiply P(A) × P(B). Option 4 is also correct mathematically (by symmetry), but option 2 follows the standard formulation.
============================================================

Accept this flashcard? (yes/no/edit/skip): yes

✓ Flashcard saved! (ID: 142)

What would you like to create a flashcard about? (or type 'done' to finish)

User: done

Claude: Great! You've created 1 flashcard for "Conditional Probability Basics".

To export this set for your live site, run:

  python manage.py export_flashcards --topic "Probability"

This will create a JSON file you can transfer to your live server and import.
```