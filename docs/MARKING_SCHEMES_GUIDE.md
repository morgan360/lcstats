# Marking Schemes Guide

## Overview

Marking schemes reach students in two forms, both of them images or PDFs. There
is no structured marking-scheme record in the database: a `MarkingScheme` model
with a JSON breakdown, examiner notes and national averages was designed on
2025-11-28 and deleted the next day (migration `0003_delete_markingscheme`) in
favour of the PDF upload added in `0002`. Do not reintroduce it — exam content is
deliberately not stored as text. See the CLAUDE.md note "Upload solution images
to question parts, marking scheme PDFs to papers (not JSON marking schemes)".

| What | Field | Who sees it |
|---|---|---|
| Full scheme for a paper | `ExamPaper.marking_scheme_pdf` | Students, as a download link on the paper list and papers-and-solutions pages |
| Per-part scheme crop | `ExamQuestionPart.solution_image` | Students, as the solution after unlock; also the reference image for vision grading |

## Workflow

### 1. Download the official PDFs

```bash
python manage.py download_lc_papers --start-year 2026 --end-year 2026 --schemes-only
```

Files land in `media/exam_papers/lc_downloads/` as `LC_HL_maths_<year>_MS.pdf`.
Existing files are skipped, so re-running is safe. The command defaults to
`--end-year 2025`, so a new year needs the flag explicitly.

### 2. Attach the paper-level PDF

In `/admin/exam_papers/exampaper/`, upload the scheme into the **Marking scheme
PDF** field under "Resources" and save. That alone gives students the download
link.

### 3. Attach per-part crops

For each `ExamQuestionPart`, upload the relevant slice of the scheme into
**Solution image**. This is the part that matters for grading: it is what
`grade_with_vision_marking_scheme()` shows the model when marking an answer.
A part with no crop still grades, but without a scheme to mark against.

Solutions unlock for a student after a correct answer, or once attempts reach
`solution_unlock_after_attempts` (default 2; set 0 for always visible).

### 4. Fill in per-part marks

```bash
python manage.py auto_extract_marking_info <paper_id> --dry-run
```

Reads `max_marks` off each part's scheme crop with the vision model. Drop
`--dry-run` to save; add `--overwrite` to replace marks that are already set
(the default is to fill blanks only), and `--question N` to limit the run.

**How marks appear in LC schemes:** not as a mark count but as a scale —
`Scale 10C (0, 3, 7, 10)` means the part is worth 10, awarded at 0, 3, 7 or 10.
The `Model Solution – 30 Marks` heading is the total for the whole question, not
the part, and must not be used. The extraction prompt in
`exam_papers/services/vision_grading.py` explains both points to the model;
if extraction starts returning zeros, check that prompt first.

Vision misreads scales often enough that the marks want checking in admin before
the paper is published.

## Coverage

Schemes are published per year, covering both papers in one PDF. As of
2026-08-06 the archive is complete except **2018, 2022 and 2026** — 2026 is not
yet released by the SEC.

## Troubleshooting

**Extraction reports "could not read marks" for every part**
The crops may not include the Marking Notes column, which is where the scale
lives. A crop of the model-solution column alone has no marks in it.

**Marks come back wrong**
Check the crop is the right part's row. A crop showing `(a)` attached to part
`(c) (ii)` yields `(a)`'s marks, and nothing downstream will notice.

**A marking scheme download link 404s**
The `marking_scheme_pdf` field points at a path under `MEDIA_ROOT`. If the row
was created on another machine, the file may not have been copied across.

## Admin URLs

- Exam papers: `/admin/exam_papers/exampaper/`
- Question parts: `/admin/exam_papers/examquestionpart/`
