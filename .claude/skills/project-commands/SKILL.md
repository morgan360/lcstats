---
description: Run this project's custom manage.py commands - downloading and extracting LC exam papers, reading part marks off marking schemes, tagging question and part topics, building worksheets, database backups, the daily student report, flashcard import/export, and syncing the Summary Notes and Cheat Sheet PDFs. Read before invoking any of them, because several carry traps their --help text does not explain (legacy paper layouts, the parts-sum-to-total check).
name: project-commands
---

# Project management commands

## Exam papers
```bash
# Download LC exam papers
python manage.py download_lc_papers

# Download the deferred sitting instead (2022 onwards, Higher Level, English
# version). These have no predictable URL: the paths come from walking the
# archive's search form, so the years on offer are read from the site and
# --start-year/--end-year only narrow that list.
python manage.py download_lc_papers --deferred --dry-run
python manage.py download_lc_papers --deferred

# Extract questions from exam PDFs (--auto reads structure from the text layer,
# --dry-run shows what was detected without writing). Both paths fill only
# blanks, so re-running never disturbs work done by hand.
python manage.py extract_exam_questions <paper_id> --auto

# Papers before 2012 Paper 2 number questions "1." and fit two to a page, so
# they need --legacy, which crops each question out of the page by position.
python manage.py extract_exam_questions <paper_id> --legacy --dry-run

# Fill in question part max_marks from the marking scheme. Reads the
# "Scale 10C (0, 3, 7, 10)" notation out of the scheme's text layer, summing
# every scale in a part's region -- a part covering (i) and (ii) carries one
# scale each and is worth both. Falls back to reading the crop with vision
# (needs solution_image) only where there is no usable text; --no-vision
# forbids even that. Fills blanks only unless --overwrite.
#
# Each question's parts are checked against its total, which is known
# independently from the paper, and a question that does not add up is left
# alone rather than written wrong. That check is ON by default; turn it off
# with --no-verify-total only when the question totals are themselves wrong.
python manage.py auto_extract_marking_info <paper_id> --dry-run

# Give every question part its one topic. Writes straight to the database,
# overwriting what is there. Part topics are never shown; they only feed the
# next command.
python manage.py tag_part_topics <paper_id> --dry-run
python manage.py tag_part_topics <paper_id>

# Fill a question's blank main / secondary / need-to-know topics from its part
# marks (secondary ticked for listing at >= 1/3 of the marks). Blanks only
# unless --overwrite; review on /exam-papers/worksheet/ afterwards.
python manage.py tag_question_topics --paper <paper_id> --dry-run


# Populate answer format fields
python manage.py populate_answer_formats

# Import exam paper (interactive_lessons)
python manage.py import_exam_paper

# Import marking scheme (interactive_lessons)
python manage.py import_marking_scheme
```

## Worksheets
`/exam-papers/worksheet/` picks questions by topic and either prints them or
downloads a PDF (`exam_papers/services/worksheet_pdf.py`, images re-encoded at
150 DPI so a sheet stays emailable).
```bash
```

## Students
```bash
# Generate daily student progress report
python manage.py daily_student_report

# Log out all active users
python manage.py logout_all_users
```

## Database backup
```bash
# Create database backup
python manage.py backup_database

# Create compressed backup (recommended for production)
python manage.py backup_database --compress

# Keep backups for 60 days (default: 30)
python manage.py backup_database --keep-days 60

# Custom backup directory
python manage.py backup_database --backup-dir /path/to/backups
```

## Flashcards
```bash
# Import flashcards from JSON
python manage.py import_flashcards path/to/flashcards.json

# Export flashcards to JSON
python manage.py export_flashcards --topic "Topic Name"
```

## Summary Notes and Cheat Sheets
```bash
# Load the PDFs built in ~/maths (build-cheatsheets.sh -> Summary Notes,
# build-cheatsheets-short.sh -> Cheat Sheets) into CheatSheet rows, one of each
# per topic. Dry run by default; the stem -> topic-slug map lives in the command.
python manage.py sync_sheets
python manage.py sync_sheets --apply

# Also delete Cheat Sheet rows on topics the map doesn't fill. A row taken over
# from an old hand-uploaded PDF has that file deleted either way.
python manage.py sync_sheets --apply --delete-legacy

# Production has no ~/maths: copy both build folders up and point at them.
python manage.py sync_sheets --notes-dir DIR --sheets-dir DIR --apply
```
It checks every PDF and topic slug before writing anything, so a missing build
or a renamed topic changes nothing. The Log Tables booklet is a `reference` row
and is never touched.
