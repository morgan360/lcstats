# Exam Paper Import Guide

This guide explains how to import LC Maths exam papers and marking schemes into the system.

## Prerequisites

Install the required PDF processing libraries:

```bash
pip install PyPDF2 pdf2image Pillow
```

### macOS Additional Setup

You also need `poppler` for PDF to image conversion:

```bash
brew install poppler
```

### Linux Additional Setup

```bash
sudo apt-get install poppler-utils
```

## Workflow

### Step 1: Import Exam Paper

Import the exam paper PDF and assign questions to topics interactively:

```bash
python manage.py import_exam_paper /path/to/LC_2024_Paper1.pdf --year 2024 --paper p1
```

**What happens:**
- Script extracts text and images from the PDF
- Attempts to parse questions automatically
- For each question, you'll be prompted to:
  - Select a topic (Probability, Statistics, Calculus, etc.)
  - Assign relevant images from the PDF
- Creates Question and QuestionPart objects in the database

**Optional parameters:**
- `--start-page 1` - Start from a specific page (default: 1)
- `--end-page 10` - End at a specific page (processes all pages if not specified)

### Step 2: Import Marking Scheme

After importing the exam paper, import the corresponding marking scheme:

```bash
python manage.py import_marking_scheme /path/to/LC_2024_Paper1_Scheme.pdf --year 2024 --paper p1
```

**What happens:**
- Script extracts marking information from the PDF
- Matches questions by year and paper type
- Updates existing questions with:
  - Expected answers
  - Mark allocations (max_marks)
  - Full worked solutions
  - Marking criteria

### Step 3: Review in Admin

1. Go to Django admin: `http://localhost:8000/admin/`
2. Navigate to `Interactive Lessons > Questions`
3. Filter by:
   - Is exam question: Yes
   - Exam year: 2024
   - Paper type: Paper 1

4. Review and edit:
   - Check that questions are assigned to correct topics
   - Verify images are attached correctly
   - Add/edit answers for auto-grading
   - Set `expected_type` for each QuestionPart (numeric, expression, etc.)

## Example Complete Workflow

```bash
# 1. Import 2024 Paper 1
python manage.py import_exam_paper ~/Downloads/LC_2024_P1.pdf --year 2024 --paper p1

# During import:
# Question 1 found...
# Available topics:
#   1. Probability
#   2. Statistics
#   3. Calculus
#   ...
# Select topic number: 1
# Assign images? y/n: y
# ...

# 2. Import marking scheme
python manage.py import_marking_scheme ~/Downloads/LC_2024_P1_Scheme.pdf --year 2024 --paper p1

# 3. Repeat for Paper 2
python manage.py import_exam_paper ~/Downloads/LC_2024_P2.pdf --year 2024 --paper p2
python manage.py import_marking_scheme ~/Downloads/LC_2024_P2_Scheme.pdf --year 2024 --paper p2
```

## Tips for Best Results

### PDF Quality
- Use official exam papers (not scanned/photocopied if possible)
- Ensure PDFs are text-based, not scanned images
- If using scanned PDFs, run OCR first

### Question Parsing
- The script attempts to auto-detect questions numbered "Question 1", "1.", etc.
- If parsing fails, you may need to manually create questions in Django admin
- Check the parsed text carefully during import

### Image Assignment
- Images are extracted per page
- Assign images that contain diagrams, graphs, or tables
- You can skip image assignment and add them manually later

### Topic Assignment
- Create all necessary topics in Django admin before importing
- Common topics for LC Maths:
  - Probability
  - Statistics
  - Calculus (Differentiation)
  - Calculus (Integration)
  - Algebra
  - Functions and Graphs
  - Sequences and Series
  - Complex Numbers
  - Trigonometry
  - Geometry

### Marking Schemes
- Always import the exam paper BEFORE the marking scheme
- The marking scheme import uses pattern matching - review results carefully
- You may need to manually adjust marks/answers in admin

## Database Schema

Questions are stored with these key fields:

**Question:**
- `is_exam_question` - Boolean flag for exam questions
- `exam_year` - Year (e.g., 2024)
- `paper_type` - 'p1' or 'p2'
- `source_pdf_name` - Original filename for reference
- `topic` - Foreign key to Topic
- `order` - Question number on paper

**QuestionPart:**
- `label` - Part label (e.g., "(a)", "(b)")
- `prompt` - Question text
- `answer` - Expected answer
- `max_marks` - Marks available
- `solution` - Worked solution from marking scheme
- `expected_type` - How to grade (numeric, expression, etc.)

## Troubleshooting

### "Missing dependencies" error
Install PDF libraries: `pip install PyPDF2 pdf2image Pillow`

### Images not extracting
Install poppler: `brew install poppler` (macOS) or `sudo apt-get install poppler-utils` (Linux)

### Questions not parsing correctly
- Check PDF text extraction quality
- Use `--start-page` and `--end-page` to process specific sections
- Fall back to manual entry in Django admin if needed

### Marking scheme not matching
- Ensure exam year and paper type match exactly
- Check that the exam paper was imported first
- Review the matching logic in the script

## Making Content Available to Claude

Once imported, exam questions are:

1. **Searchable by students** - Through the interactive lessons interface
2. **Trackable** - Student attempts and progress are recorded
3. **Gradeable** - Automatic grading via your existing stats_tutor.py logic
4. **Available to InfoBot** - Can be referenced in RAG system by:
   - Creating Notes that reference exam questions
   - Adding exam question solutions to the Notes system
   - Students can ask "How do I solve 2024 Paper 1 Q3?"

### Optional: Link to RAG System

To make exam papers more discoverable by Claude/InfoBot:

```python
# In Django shell
from notes.models import Note
from interactive_lessons.models import Question, Topic

# Create summary notes for each exam paper
q = Question.objects.filter(exam_year=2024, paper_type='p1').first()
Note.objects.create(
    title="LC 2024 Paper 1 - Probability Questions",
    topic=Topic.objects.get(name="Probability"),
    content="Past exam questions from LC 2024 Paper 1 covering probability...",
    metadata="2024 exam, paper 1, probability, past papers, sample questions"
)
```

This allows InfoBot to:
- Find relevant past exam questions when students ask
- Reference official marking schemes
- Suggest similar exam questions for practice