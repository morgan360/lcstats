# Flashcard Generator Skill

This skill helps create flashcards for the NumScoil flashcard system by generating multiple-choice questions with AI assistance. Supports **single card** and **batch mode** (from LaTeX files).

## Overview

Generate flashcards from text, questions, images, or LaTeX notes using Claude AI. The skill creates flashcards directly in your local database, which you can then export using `python manage.py export_flashcards` for import on the live site via the web import page at `/flashcards/import/`.

## How It Works

1. **User provides input**: Text statement, question, image, or `.tex` file path
2. **AI generates flashcard(s)**: Creates question, correct answer, 3 distractors, and explanation
3. **User reviews and confirms**: Preview the flashcard(s) before saving
4. **Save to database**: Creates FlashcardSet (if needed) and Flashcard records
5. **Export for deployment**: Export JSON and upload via `/flashcards/import/`

## Batch Mode (LaTeX Files)

When user provides a `.tex` file path:

1. **Read the LaTeX file** using the Read tool
2. **Identify key concepts**: definitions, theorems, formulas, important results
3. **Generate 10-20 flashcards** covering the material comprehensively
4. **Present all cards** in a numbered list for review
5. **Save all approved cards** to the database in one batch
6. **Auto-export** the JSON file for upload

### Batch Workflow

```
User: /flashcard-generator /Users/morgan/Downloads/maths-notes/sections/probability.tex

Claude:
1. Reads the .tex file
2. Identifies ~15 key concepts
3. Generates flashcards for each
4. Shows numbered preview of all cards
5. Asks: "Accept all? Or list numbers to exclude (e.g., 3,7,12)"
6. Saves accepted cards to DB
7. Runs: python manage.py export_flashcards --topic "Topic Name"
8. Tells user: "Upload the exported JSON at /flashcards/import/"
```

### LaTeX Parsing Guidelines

- Extract from `\begin{definition}...\end{definition}`, `\begin{theorem}...\end{theorem}`
- Identify key formulas in `\[...\]` or `$$...$$` blocks
- Look for `\textbf{...}` or `\emph{...}` for important terms
- Convert LaTeX math to KaTeX-compatible format (most LaTeX works as-is)
- Replace `\begin{align*}` with `$$` blocks for flashcard display
- Keep `\frac`, `\sqrt`, `\int`, `\sum` etc. as-is (KaTeX supports them)

## Flashcard Structure

Each flashcard must have:
- **Front** (`front_text`): Question text (supports LaTeX with `$...$` or `$$...$$`)
- **Back** (`back_text`): Correct answer text
- **Distractors**: 3 incorrect options (`distractor_1`, `distractor_2`, `distractor_3`)
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

### LaTeX File Input (Batch Mode)
User provides path to a `.tex` file, and AI:
- Reads and parses the LaTeX content
- Identifies 10-20 key concepts per file
- Generates a full flashcard for each concept
- Presents batch preview for review
- Saves all accepted cards at once

## Workflow

### Initial Setup
1. Ask user for topic/set name (or infer from LaTeX file name)
2. Check if `FlashcardSet` exists for this topic
3. If not, create new set linked to appropriate `Topic` from `interactive_lessons`

### Single Card Generation Loop
For each flashcard:

1. **Get Input**
   - Prompt: "Provide a statement, question, or image for the flashcard"
   - If image: Use Read tool to analyze it
   - If text: Process directly

2. **Generate Flashcard Content**
   - Use Claude AI to create:
     - Question (front_text)
     - Correct answer (back_text)
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
       front_text="Question text with $LaTeX$ if needed",
       back_text="Correct answer",
       distractor_1="Wrong option 1",
       distractor_2="Wrong option 2",
       distractor_3="Wrong option 3",
       explanation="Detailed explanation...",
       order=next_order,
   )
   ```

6. **Continue or Finish**
   - Ask: "Add another flashcard to this set? (yes/no)"
   - If no: Provide export instructions

### Batch Card Generation (LaTeX)
1. Read `.tex` file with Read tool
2. Parse content, identify key concepts
3. Generate all flashcards
4. Present numbered list preview
5. Ask user to confirm all or exclude specific numbers
6. Save accepted cards in one batch
7. Export JSON automatically

### Completion / Deployment
When user is done:
```bash
# Export the set
python manage.py export_flashcards --topic "Topic Name"

# Then upload the JSON file at:
# https://your-site.com/flashcards/import/
# (staff login required)
```

## AI Generation Guidelines

### Question Quality
- **Clear and unambiguous**: Question should have one definitively correct answer
- **Appropriate difficulty**: Match the LC Higher Level standard
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

## Database Models Reference

```python
# flashcards/models.py

class FlashcardSet(models.Model):
    topic = models.ForeignKey('interactive_lessons.Topic', on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=False)

class Flashcard(models.Model):
    flashcard_set = models.ForeignKey(FlashcardSet, on_delete=models.CASCADE, related_name='cards')
    front_text = models.TextField()       # Question
    back_text = models.TextField()        # Correct answer
    distractor_1 = models.TextField()
    distractor_2 = models.TextField()
    distractor_3 = models.TextField()
    explanation = models.TextField(blank=True)
    front_image = models.ImageField(upload_to='flashcards/front/', blank=True, null=True)
    back_image = models.ImageField(upload_to='flashcards/back/', blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
```

## Important Notes

### LaTeX Sanitization
- The flashcard model does NOT auto-sanitize LaTeX like Question models
- Ensure proper delimiters: `$...$` for inline, `$$...$$` for display
- Frontend renders using markdown-katex extension

### Mastery States
- New flashcards start in "new" state
- Student progression: new -> learning -> know -> retired
- Don't set initial state - let the system handle it

### Export/Import Workflow
```bash
# After creating flashcards locally:
python manage.py export_flashcards --topic "Probability"

# This creates: flashcards_export_probability_YYYYMMDD.json

# Option 1: Upload via web interface (no SSH needed)
# Go to /flashcards/import/ (staff login required)

# Option 2: CLI on server
python manage.py import_flashcards flashcards_export_probability_YYYYMMDD.json
```

### Validation
Before saving, validate:
- All required fields are non-empty
- Distractors are different from correct answer
- Distractors are different from each other
- LaTeX syntax is valid (check matching delimiters)

## Best Practices

1. **Batch by topic**: Create full sets at once for consistency
2. **Review before export**: Test flashcards locally before live import
3. **Consistent naming**: Use clear, descriptive set names
4. **Order matters**: Cards are displayed in `order` field sequence
5. **Quality over quantity**: Better to have 10 great cards than 50 mediocre ones
6. **Use batch mode for LaTeX**: Much faster than one-by-one for existing notes