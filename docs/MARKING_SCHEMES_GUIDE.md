# Marking Schemes Guide

## Overview

Marking schemes are uploaded **separately** from exam papers and provide:
- Detailed breakdown of how marks are allocated
- Common errors students make
- Partial credit guidelines
- Enhanced feedback during grading

## Workflow

### 1. Upload Marking Scheme PDF

In Django admin (`/admin/exam_papers/exampaper/`):
1. Navigate to the exam paper you want to add a marking scheme for
2. Scroll to the **"Marking scheme PDF"** field
3. Upload the official marking scheme PDF
4. Save the exam paper

### 2. Extract Marking Scheme Pages

Run the management command to extract pages per question:

```bash
python manage.py extract_marking_scheme <paper_id> --page-ranges "1:1-2,2:3-4,3:5-6"
```

**Format:** `question_number:start_page-end_page`

**Example:**
```bash
python manage.py extract_marking_scheme 1 --page-ranges "1:1-2,2:3-4,3:5-6,4:7-8"
```

This creates `MarkingScheme` objects for each question part.

### 3. Add Detailed Marking Breakdown

In Django admin (`/admin/exam_papers/markingscheme/`):

Edit each marking scheme and fill in the **"Marking breakdown"** JSON field:

```json
{
  "steps": [
    {
      "description": "Correctly identify the sine rule formula",
      "marks": 1
    },
    {
      "description": "Substitute values correctly into formula",
      "marks": 2
    },
    {
      "description": "Simplify to find final answer",
      "marks": 2
    }
  ],
  "common_errors": [
    "Forgetting to convert degrees to radians",
    "Sign error when determining quadrant",
    "Using cosine rule instead of sine rule"
  ],
  "partial_credit_notes": "Award 1 mark for correct approach even if arithmetic error occurs"
}
```

### 4. Optional: Add Examiner Notes

In the **"Examiner notes"** field, add any additional guidance:

```
Students often struggle with identifying which rule to apply.
Accept alternative methods using triangulation.
```

### 5. Optional: Add National Statistics

If available, add the **national mean score** (as a percentage):

```
45.2
```

## How Marking Schemes Enhance Student Experience

### During Answer Submission

When a student submits an **incorrect or partially correct** answer:

1. **Base feedback** from automated grading
2. **Plus:** Common errors (first 2)
3. **Plus:** Mark breakdown steps (first 3)
4. **Plus:** Partial credit notes (if applicable)

**Example feedback:**
```
Partially correct — one element of your answer matches.

Common mistakes to avoid:
• Forgetting to convert degrees to radians
• Sign error when determining quadrant

Marking breakdown:
• Correctly identify the sine rule formula (1 mark)
• Substitute values correctly into formula (2 marks)
• Simplify to find final answer (2 marks)

Note: Award 1 mark for correct approach even if arithmetic error occurs
```

### In Results View

Students can expand each question part to see:

1. ✅ **Correct Answer**
2. 📋 **Full Marking Scheme** including:
   - Mark allocation per step
   - All common errors
   - Partial credit guidelines
   - Examiner notes
   - National average (if available)
3. 📖 **Worked Solution** (text and/or image)

## JSON Structure Reference

```json
{
  "steps": [
    {"description": "Step description", "marks": 1},
    {"description": "Another step", "marks": 2}
  ],
  "common_errors": [
    "Error 1",
    "Error 2",
    "Error 3"
  ],
  "partial_credit_notes": "Text describing partial credit rules"
}
```

**Fields:**
- `steps` (array): List of marking steps, each with:
  - `description` (string): What the student needs to do
  - `marks` (number): Marks allocated for this step

- `common_errors` (array of strings): Common mistakes students make

- `partial_credit_notes` (string): Guidelines for awarding partial credit

## Preview Mode

To preview PDF structure before extracting:

```bash
python manage.py extract_marking_scheme <paper_id> --preview
```

This shows:
- Total pages
- Metadata
- Page dimensions

## Tips for Best Results

1. **Separate marking scheme PDFs**
   - Upload marking schemes separately from question papers
   - Use clear page ranges for each question

2. **Detailed marking breakdowns**
   - Break down marks into clear steps
   - Include all possible approaches
   - Note where alternative methods are acceptable

3. **Common errors**
   - List the most frequent mistakes
   - Help students learn from typical pitfalls
   - Based on examiner reports if available

4. **Partial credit**
   - Clearly state when partial marks apply
   - Helps students understand grading
   - Encourages showing working

5. **National statistics**
   - Add if available from SEC reports
   - Helps students gauge difficulty
   - Provides context for their performance

## Example: Complete Workflow

```bash
# 1. Upload PDFs in admin
# - Exam paper PDF
# - Marking scheme PDF

# 2. Extract exam questions
python manage.py extract_exam_questions 5 --page-ranges "1:1-2,2:3-4,3:5-6"

# 3. Extract marking schemes
python manage.py extract_marking_scheme 5 --page-ranges "1:1-2,2:3-4,3:5-6"

# 4. In admin, for each question part, add JSON marking breakdown
# 5. Fill in question prompts, answers, solutions
# 6. Publish the paper
```

## Database Structure

```
ExamPaper
  └─ marking_scheme_pdf (FileField)

ExamQuestionPart
  └─ MarkingScheme (OneToOne)
       ├─ marking_breakdown (JSONField)
       ├─ examiner_notes (TextField)
       └─ national_mean_score (FloatField)
```

## Troubleshooting

**Q: Marking scheme extraction fails**
- Check PDF is valid and not corrupted
- Verify page numbers are correct (1-indexed)
- Ensure question exists in database first

**Q: JSON validation error**
- Verify JSON structure matches example above
- Check for missing commas, quotes
- Use JSON validator online

**Q: Marking scheme not showing in results**
- Check marking scheme exists for question part
- Verify marking_breakdown has valid JSON
- Ensure student has completed the attempt

**Q: National average not displaying**
- Must be a number (not percentage symbol)
- Example: `45.2` not `45.2%`

## Admin URLs

- Exam Papers: `/admin/exam_papers/exampaper/`
- Marking Schemes: `/admin/exam_papers/markingscheme/`
- Question Parts: `/admin/exam_papers/examquestionpart/`

---

**Summary**: Marking schemes provide rich educational feedback, helping students learn from mistakes and understand how marks are allocated. Upload separately from exam papers and structure as detailed JSON for best results.