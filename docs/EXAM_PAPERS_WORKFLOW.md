# Exam Papers Management Workflow

Complete guide for uploading and managing Leaving Certificate exam papers in the LCAI Maths platform.

## Overview

The exam papers system provides:
- ✅ Separate database models for exam papers
- ✅ PDF upload and automatic question extraction
- ✅ Image preview alongside admin forms for easy transcription
- ✅ Structured marking schemes
- ✅ Timer tracking (paper-level and question-level)
- ✅ Graduated solution access based on attempts
- ✅ Dual organization (by year AND by topic)

---

## Workflow: Adding a New Exam Paper

### Step 1: Upload the PDF

1. Go to Django Admin: `/admin/exam_papers/exampaper/`
2. Click "Add Exam Paper"
3. Fill in basic information:
   - **Year**: 2024
   - **Paper Type**: Paper 1 or Paper 2
   - **Title**: Auto-generated (e.g., "Leaving Certificate 2024 Paper 1")
   - **Time Limit**: 150 minutes (default)
   - **Total Marks**: e.g., 300
   - **Instructions**: Optional (e.g., "Answer 6 out of 8 questions")
4. Upload the **Source PDF** file
5. **Save** the paper

---

### Step 2: Preview PDF and Plan Extraction

1. After saving, expand the "Resources" section
2. You'll see:
   - PDF embedded in an iframe
   - Command examples for extraction

3. **First, preview the PDF structure:**
   ```bash
   python manage.py extract_exam_questions <paper_id> --preview
   ```

   This shows:
   - Total pages
   - Page dimensions
   - Metadata -

Example output:
```
=== PDF Info for 2024 Paper 1 ===
Total pages: 16
Metadata: {'title': 'LC 2024 P1', ...}
Page details:
  Page 1: 595x842 pts
  Page 2: 595x842 pts
  ...
```

---

### Step 3: Extract Question Images

You have two options:

#### Option A: Automatic Splitting (Equal Distribution)
Best for papers where questions are evenly distributed.

```bash
python manage.py extract_exam_questions <paper_id> --num-questions 8
```

This automatically:
- Splits PDF into 8 equal parts
- Creates ExamQuestion records (Q1-Q8)
- Extracts and saves question images

#### Option B: Manual Page Ranges (Recommended)
Best for precise control. Specify exactly which pages contain each question.

```bash
python manage.py extract_exam_questions <paper_id> --page-ranges "1:1-2,2:3-4,3:5-6,4:7-8,5:9-10,6:11-12,7:13-14,8:15-16"
```

Format: `question_number:start_page-end_page`

**Multi-page questions**: If a question spans pages 2-3, the images are automatically combined vertically.

---

### Step 4: Fill in Question Details

After extraction, questions appear in the admin with placeholder data.

1. Go to `/admin/exam_papers/examquestion/`
2. Filter by your exam paper (year/paper type)
3. Click on each question to edit

#### For Each Question:

**Question Identification:**
- Question number: Already set (1, 2, 3, etc.)
- Order: Already set

**Content:**
- **Topic**: Select from dropdown (e.g., "Trigonometry (2)")
- **Title**: Optional description (e.g., "Compound Angles and Double Angles")
- **Stem**: Question introduction (if shared by all parts)
- **Image**: Already extracted - **you'll see a preview!**

**The Image Preview shows:**
- Full question image from PDF
- Reference for manual transcription
- Suggestion to use `/extract-question` command

**Marking & Timing:**
- **Total Marks**: Sum of all parts (e.g., 25)
- **Suggested Time**: Minutes for this question (e.g., 20)

---

### Step 5: Add Question Parts

Scroll down to "Exam question parts" inline section.

#### For Each Part (a), (b), (c), etc.:

**Part Identification:**
- **Label**: (a), (b), (c), (i), (ii), etc.
- **Order**: 0, 1, 2, ...

**Question Content:**
- **Prompt**: The actual question text with KaTeX
  - Example: `Find the general solution of $\tan 3\theta = \sqrt{3}$`
- **Image**: Optional diagram for this specific part
- **Expected Format**: What answer format to expect
  - Example: `"General solution in degrees (e.g., $\theta = 45° + 180°n$)"`

**Answer:**
- **Answer**: Correct answer(s)
  - Example: `$\theta = 20° + 60°n$`
- **Expected Type**:
  - `exact` - Exact text match
  - `numeric` - Number with tolerance
  - `expression` - Algebraic expression
  - `multi` - Multiple choice
  - `manual` - Requires manual grading

**Solution:**
- **Solution**: Worked solution in steps
  ```
  **Step 1:** Identify the formula

  $\tan 2\theta = \frac{2\tan\theta}{1-\tan^2\theta}$

  **Step 2:** Substitute values...
  ```
- **Solution Image**: Optional solution diagram
- **Solution Unlock After Attempts**: Default 2 (students see solution after 2 tries)

**Marking:**
- **Max Marks**: Points for this part (e.g., 3)

---

### Step 6: Add Marking Scheme (Optional but Recommended)

After creating question parts, add detailed marking schemes:

1. In ExamQuestionPart admin, click "Add Marking Scheme" inline
2. Enter JSON format:

```json
{
  "steps": [
    {"description": "Identify correct formula", "marks": 1},
    {"description": "Substitute values correctly", "marks": 1},
    {"description": "Simplify to final answer", "marks": 2},
    {"description": "State general solution", "marks": 1}
  ],
  "common_errors": [
    "Forgetting period is 180° for tangent",
    "Not dividing by coefficient after formula application"
  ],
  "partial_credit_notes": "Award 3/5 if formula correct but arithmetic error in final step"
}
```

**Optional Fields:**
- **Examiner Notes**: Additional guidance
- **National Mean Score**: If available (e.g., 62.5%)

---

### Step 7: Publish the Paper

1. Go back to ExamPaper admin
2. Check **"Is Published"** checkbox
3. **Save**

Paper is now visible to students!

---

## Using /extract-question Command (Alternative)

Instead of manual entry in Step 5, you can use your existing extraction skill:

1. After Step 4, note the question image URL in admin
2. In Claude Code, run:
   ```
   /extract-question
   ```
3. When prompted, provide the image URL from admin
4. Claude extracts and formats the question with KaTeX
5. Copy-paste into admin forms

---

## Question Types and Answer Formats

### Numeric Questions
- **Expected Type**: `numeric`
- **Answer**: Just the number (e.g., `30,60,210,240`)
- **Expected Format**: `"Multiple values separated by commas (e.g., 45,135,225)"`

### Expression Questions
- **Expected Type**: `expression`
- **Answer**: With KaTeX (e.g., `$\frac{2}{7}$,-$\frac{7}{2}$`)
- **Expected Format**: `"Two values separated by comma (e.g., $\frac{3}{5}$,-$\frac{5}{3}$)"`

### Multiple Choice
- **Expected Type**: `multi`
- **Answer**: Correct option (e.g., `A`)
- **Prompt**: Include options in question text

### Manual Grading
- **Expected Type**: `manual`
- Use for proofs, explanations, or complex answers
- Teacher reviews in admin

---

## Tips for Efficient Entry

### 1. Use Copy-Paste from PDF
- Open PDF in separate tab
- Copy text directly (preserves some formatting)
- Add KaTeX delimiters manually

### 2. Batch Process Similar Questions
- Group questions by topic
- Reuse marking scheme structures
- Copy solution templates

### 3. Use Page Ranges for Precision
Always use `--page-ranges` for real papers:
```bash
# Example: LC 2024 P1 with 8 questions
python manage.py extract_exam_questions 1 --page-ranges \
  "1:1-2,2:3-4,3:5-6,4:7-8,5:9-10,6:11-12,7:13-14,8:15-16"
```

### 4. Verify Topic Assignment
- Ensures questions appear in correct topic practice
- Enables "revision by topic" feature
- Critical for student navigation

---

## Viewing Exam Papers (Student Side)

Students will access papers via:

**By Year:**
- `/exam-papers/` → Browse all papers
- `/exam-papers/2024-p1/` → Full paper view
- Timer starts automatically in "Full Timed" mode

**By Topic:**
- `/interactive/trigonometry-2/sections/` → Shows all sections
- Exam questions appear in sections like "2024 Paper 1"
- No timer in practice mode
- Graduated solution access applies

---

## Database Structure

```
ExamPaper (2024 Paper 1)
├── ExamQuestion (Q1)
│   ├── image (extracted from PDF)
│   ├── topic → Trigonometry (2)
│   └── ExamQuestionPart (a)
│       ├── answer, solution
│       └── MarkingScheme (structured JSON)
│   └── ExamQuestionPart (b)
│       └── MarkingScheme
├── ExamQuestion (Q2)
│   └── ...
└── ExamAttempt (student's attempt)
    ├── timer data
    └── ExamQuestionAttempt (for each part)
        ├── student_answer
        ├── marks_awarded
        └── time_spent
```

---

## Troubleshooting

### "No questions extracted"
- Check PDF has actual pages (not just a cover)
- Try `--preview` first to verify page count
- Ensure PDF is not password-protected

### "Images look wrong"
- Multi-page questions: Use page ranges to combine
- Adjust DPI if needed (edit `utils.py`)
- Manually upload better image if needed

### "Can't see image preview in admin"
- Check MEDIA_ROOT and MEDIA_URL in settings.py
- Verify image file exists in media folder
- Check file permissions

### "KaTeX not rendering"
- Use `$...$` for inline math
- Use `$$...$$` for display math
- Never use `\(...\)` or `\[...\]`

---

## Next Steps

After adding papers:
1. **Test student workflow** (views coming next)
2. **Add more papers** (build question bank)
3. **Migrate existing exam questions** from `interactive_lessons`
4. **Create analytics dashboard** for performance tracking

---

## Command Reference

```bash
# Preview PDF structure
python manage.py extract_exam_questions <paper_id> --preview

# Automatic extraction (8 questions)
python manage.py extract_exam_questions <paper_id> --num-questions 8

# Manual page ranges (precise)
python manage.py extract_exam_questions <paper_id> --page-ranges "1:1-2,2:3-4,..."

# Example for LC 2024 Paper 1 (paper_id=1, 8 questions, 2 pages each)
python manage.py extract_exam_questions 1 --page-ranges \
  "1:1-2,2:3-4,3:5-6,4:7-8,5:9-10,6:11-12,7:13-14,8:15-16"
```

---

## Admin URLs

- **Exam Papers**: `/admin/exam_papers/exampaper/`
- **Questions**: `/admin/exam_papers/examquestion/`
- **Question Parts**: `/admin/exam_papers/examquestionpart/`
- **Marking Schemes**: `/admin/exam_papers/markingscheme/`
- **Attempts**: `/admin/exam_papers/examattempt/`

---

**Ready to add your first exam paper!** 🎓