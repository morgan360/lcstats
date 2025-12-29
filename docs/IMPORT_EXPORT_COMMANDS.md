# Import/Export Commands Reference

Quick reference for all data import and export commands in the NumScoil project.

## Database Sync (Questions & Notes)

### Export from Local
```bash
# Export questions, sections, and topics
python manage.py dumpdata interactive_lessons.Topic interactive_lessons.Section interactive_lessons.Question interactive_lessons.QuestionPart --indent 2 > questions_$(date +%Y%m%d_%H%M%S).json

# Export notes
python manage.py dumpdata notes.Note --indent 2 > notes_$(date +%Y%m%d_%H%M%S).json

# Or use the automated script
./deployment/sync_to_production_simple.sh
```

### Import to Production
```bash
# On PythonAnywhere
cd ~/lcstats
source venv/bin/activate

python manage.py loaddata questions_YYYYMMDD_HHMMSS.json
python manage.py loaddata notes_YYYYMMDD_HHMMSS.json

touch /var/www/morganmck_eu_pythonanywhere_com_wsgi.py
```

---

## Flashcards

### Import Flashcards
```bash
# Import flashcards from JSON export file
python manage.py import_flashcards /path/to/flashcards_export.json

# Clear existing flashcards before importing
python manage.py import_flashcards /path/to/flashcards_export.json --clear
```

**Note:** Flashcard exports include base64-encoded images. No separate image upload needed.

---

## Questions (Safe Import/Export)

### Export Questions
```bash
# Export questions safely (preserves images)
python manage.py export_questions_safe
```

### Import Questions
```bash
# Import questions from safe export
python manage.py import_questions_safe /path/to/export.json
```

---

## Notes & PDF Resources

### Import PDF Summary
```bash
# Import PDF as note summary sections
python manage.py import_summary_sections media/StatssSummary.pdf --topic "Statistics Summary"
```

### Import Markdown Docs
```bash
# Import markdown documentation as notes
python manage.py import_markdown_docs /path/to/docs/
```

---

## Exam Papers

### Import Exam Paper
```bash
# Import exam paper questions
python manage.py import_exam_paper /path/to/exam_paper.json
```

### Import Marking Scheme
```bash
# Import marking scheme for exam paper
python manage.py import_marking_scheme /path/to/marking_scheme.json
```

---

## Media Files

### Sync Media to Production
```bash
# Upload media files (images, PDFs, etc.)
./deployment/sync_media_to_production.sh
```

---

## Production Deployment Workflow

### 1. Local to Production (Complete Sync)
```bash
# LOCAL: Export data
./deployment/sync_to_production_simple.sh

# Upload JSON files via PythonAnywhere Files tab
# https://www.pythonanywhere.com/user/morganmck/files/home/morganmck/lcstats/

# PRODUCTION: Import data
cd ~/lcstats
source venv/bin/activate
python manage.py loaddata questions_YYYYMMDD_HHMMSS.json
python manage.py loaddata notes_YYYYMMDD_HHMMSS.json
touch /var/www/morganmck_eu_pythonanywhere_com_wsgi.py
```

### 2. Code Changes Only
```bash
# LOCAL: Push to GitHub
git add .
git commit -m "Your changes"
git push origin main

# PRODUCTION: Pull and reload
cd ~/lcstats
git pull origin main
touch /var/www/morganmck_eu_pythonanywhere_com_wsgi.py
```

### 3. Flashcards Only
```bash
# LOCAL: Get export file ready

# Upload flashcards_export.json via PythonAnywhere Files tab

# PRODUCTION: Import
cd ~/lcstats
source venv/bin/activate
python manage.py import_flashcards ~/lcstats/flashcards_export.json
touch /var/www/morganmck_eu_pythonanywhere_com_wsgi.py
```

---

## What Gets Synced

### Database Sync (loaddata)
✅ Topics, Sections, Questions, QuestionParts
✅ Notes (RAG knowledge base)
❌ Student data (profiles, attempts)
❌ User accounts
❌ Media files (images, PDFs)

### Flashcard Import
✅ Flashcard sets and cards
✅ Images (base64-encoded in JSON)
✅ Topic associations

### Media Sync
✅ Images (question_images/, solutions/, etc.)
✅ PDFs (exam papers, cheatsheets)
✅ Other uploaded files

---

## Troubleshooting

### Import Fails with IntegrityError
**Cause:** Data already exists
**Fix:** Data is already imported, safe to ignore

### Import Fails with Schema Error
**Cause:** Migrations not run
**Fix:** `python manage.py migrate`

### Changes Not Visible
**Cause:** Web app not reloaded
**Fix:** `touch /var/www/morganmck_eu_pythonanywhere_com_wsgi.py`

### Large Import Times Out
**Cause:** Normal for large datasets
**Fix:** Be patient, imports can take 30-60 seconds

---

## Quick Command Summary

| Task | Command |
|------|---------|
| Export questions | `python manage.py dumpdata interactive_lessons.Topic interactive_lessons.Section interactive_lessons.Question interactive_lessons.QuestionPart --indent 2 > questions.json` |
| Export notes | `python manage.py dumpdata notes.Note --indent 2 > notes.json` |
| Import questions | `python manage.py loaddata questions.json` |
| Import notes | `python manage.py loaddata notes.json` |
| Import flashcards | `python manage.py import_flashcards flashcards.json` |
| Reload web app | `touch /var/www/morganmck_eu_pythonanywhere_com_wsgi.py` |

---

## File Locations

**Production:**
- Project: `/home/morganmck/lcstats/`
- WSGI: `/var/www/morganmck_eu_pythonanywhere_com_wsgi.py`
- Venv: `/home/morganmck/lcstats/venv/`

**PythonAnywhere URLs:**
- Files: https://www.pythonanywhere.com/user/morganmck/files/
- Console: https://www.pythonanywhere.com/user/morganmck/consoles/
- Web: https://eu.pythonanywhere.com/user/morganmck/webapps/
