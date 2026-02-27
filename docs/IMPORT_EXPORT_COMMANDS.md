# Import/Export Commands Reference

Quick reference for all data import and export commands in the NumScoil project.

## ⚠️ IMPORTANT: Choose the Right Sync Method

### Use Safe Import/Export (Recommended)
**When:** Adding questions to existing topics/sections that already exist in production
**Why:** Avoids ID conflicts and "Duplicate entry" errors
**How:** See "Questions (Safe Import/Export)" section below

### Use Standard Import/Export
**When:** Creating brand new topics/sections, or setting up fresh production database
**Why:** Simpler for completely new data
**How:** See "Database Sync (Questions & Notes)" section below

---

## Questions (Safe Import/Export) - RECOMMENDED

**Use this method when adding questions to existing topics/sections in production.**

This method uses natural keys (topic/section names) instead of database IDs, preventing conflicts.

### Interactive Script (Easiest)
```bash
# LOCAL: Run interactive export script
./deployment/sync_questions_safe.sh

# Follow prompts to export by:
# - Specific question IDs, OR
# - Entire section name

# Then follow on-screen instructions for PythonAnywhere import
```

### Manual Export (Advanced)
```bash
# Export specific question IDs
python manage.py export_questions_safe --ids 123 124 125 --output new_questions.json

# OR export entire section
python manage.py export_questions_safe --section "Hypothesis Testing - Mean" --output section_export.json
```

### Import to Production
```bash
# On PythonAnywhere
cd ~/lcstats
source venv/bin/activate

# Pull latest code (important - keeps import command updated)
git pull origin main

# Import questions
python manage.py import_questions_safe questions_safe_YYYYMMDD_HHMMSS.json

# Reload web app
touch /var/www/morgan360_pythonanywhere_com_wsgi.py

# Verify import
python manage.py shell -c "from interactive_lessons.models import Section; s = Section.objects.get(name='Your Section'); print(f'{s.name}: {s.questions.count()} questions')"
```

**Key Benefits:**
- ✅ No ID conflicts
- ✅ Uses topic/section names instead of PKs
- ✅ Won't fail with "Duplicate entry 'differentiation'" errors
- ✅ Can be run multiple times safely

---

## Database Sync (Questions & Notes) - For New Topics Only

**⚠️ Use this ONLY when creating brand new topics/sections that don't exist in production yet.**

### Export from Local
```bash
# Export questions, sections, and topics (use ONLY for new topics)
python manage.py dumpdata interactive_lessons.Topic interactive_lessons.Section interactive_lessons.Question interactive_lessons.QuestionPart --indent 2 > questions_$(date +%Y%m%d_%H%M%S).json

# Export notes (safe to use anytime)
python manage.py dumpdata notes.Note --indent 2 > notes_$(date +%Y%m%d_%H%M%S).json

# Or use the automated script (for new topics + notes)
./deployment/sync_to_production_simple.sh
```

### Import to Production
```bash
# On PythonAnywhere
cd ~/lcstats
source venv/bin/activate

# ⚠️ WARNING: loaddata will FAIL if topics already exist
python manage.py loaddata questions_YYYYMMDD_HHMMSS.json

# Notes are safe to import anytime
python manage.py loaddata notes_YYYYMMDD_HHMMSS.json

touch /var/www/morgan360_pythonanywhere_com_wsgi.py
```

**Limitations:**
- ❌ Fails with "Duplicate entry" if topics/sections exist
- ❌ Requires matching database IDs
- ⚠️ Not recommended for routine question updates

---

## Subject-Specific Deployment (Maths or Physics Only)

**Use these scripts when you want to deploy only Maths or only Physics data to production.**

This is useful when:
- Production server doesn't have both subjects set up yet
- You want to deploy Maths and Physics independently
- Avoiding foreign key errors from missing Subject references

### Current Database Status

Your local database contains:
- **19 Maths topics** with 495 questions (697 question parts)
- **11 Physics topics** with 1 question (4 question parts)

### Deploy Maths Only (Merge Mode)

**Use this to ADD new questions to existing production data.**

```bash
# LOCAL: Export only Maths data
./deployment/sync_maths_only_to_production.sh

# This exports 5 files:
# - maths_topics_YYYYMMDD_HHMMSS.json (19 topics)
# - maths_sections_YYYYMMDD_HHMMSS.json (175 sections)
# - maths_questions_YYYYMMDD_HHMMSS.json (495 questions)
# - maths_parts_YYYYMMDD_HHMMSS.json (697 question parts)
# - maths_notes_YYYYMMDD_HHMMSS.json (5 notes)

# Upload files via PythonAnywhere Files tab, then:

# PRODUCTION: Import Maths data
cd ~/lcstats
source venv/bin/activate
python manage.py loaddata maths_topics_YYYYMMDD_HHMMSS.json
python manage.py loaddata maths_sections_YYYYMMDD_HHMMSS.json
python manage.py loaddata maths_questions_YYYYMMDD_HHMMSS.json
python manage.py loaddata maths_parts_YYYYMMDD_HHMMSS.json
python manage.py loaddata maths_notes_YYYYMMDD_HHMMSS.json
touch /var/www/morganmck_eu_pythonanywhere_com_wsgi.py
```

### Deploy Maths Only (REPLACE Mode) - LOCAL IS SOURCE OF TRUTH

**⚠️ Use this when local is the source of truth and you want production to be an exact copy.**

**What it does:**
- Deletes ALL existing Maths data in production
- Imports fresh data from local
- Production becomes exact mirror of local (no duplicates, no conflicts)

**When to use:**
- You have duplicate sections in production (e.g., "Argand Diagram" vs "Argand Diagrams")
- Production has old/incorrect data
- You want to ensure production exactly matches local

```bash
# LOCAL: Export Maths data and generate delete/import commands
./deployment/sync_maths_replace_production.sh

# Follow the on-screen instructions:
# 1. Upload 5 JSON files to PythonAnywhere
# 2. Run DELETE script on production (removes old Maths data)
# 3. Run IMPORT script on production (adds fresh data)
```

**⚠️ WARNING:**
- This DELETES all existing Maths topics, sections, questions, and question parts
- Student progress data (attempts, scores) is NOT deleted
- Cannot be undone - make sure local is correct before running!

**Safe Alternative:** If you only want to add NEW questions without deleting anything, use the "Merge Mode" above instead.

---

### Deploy Physics Only

```bash
# LOCAL: Export only Physics data
./deployment/sync_physics_only_to_production.sh

# This exports 5 files:
# - physics_topics_YYYYMMDD_HHMMSS.json (11 topics)
# - physics_sections_YYYYMMDD_HHMMSS.json (1 section)
# - physics_questions_YYYYMMDD_HHMMSS.json (1 question)
# - physics_parts_YYYYMMDD_HHMMSS.json (4 question parts)
# - physics_notes_YYYYMMDD_HHMMSS.json (0 notes)

# Upload files via PythonAnywhere Files tab, then:

# PRODUCTION: Import Physics data
cd ~/lcstats
source venv/bin/activate
python manage.py loaddata physics_topics_YYYYMMDD_HHMMSS.json
python manage.py loaddata physics_sections_YYYYMMDD_HHMMSS.json
python manage.py loaddata physics_questions_YYYYMMDD_HHMMSS.json
python manage.py loaddata physics_parts_YYYYMMDD_HHMMSS.json
python manage.py loaddata physics_notes_YYYYMMDD_HHMMSS.json
touch /var/www/morganmck_eu_pythonanywhere_com_wsgi.py
```

### Deploy Both Subjects (All Data)

```bash
# LOCAL: Export all topics (Maths + Physics)
./deployment/sync_to_production_simple.sh

# This exports 2 files with ALL data:
# - questions_YYYYMMDD_HHMMSS.json (ALL topics, sections, questions, parts)
# - notes_YYYYMMDD_HHMMSS.json (ALL notes)

# Use this ONLY if production server has both Maths and Physics subjects configured
```

**Key Benefits of Subject-Specific Scripts:**
- ✅ No Subject foreign key errors
- ✅ Deploy Maths and Physics independently
- ✅ Smaller export files (faster uploads)
- ✅ Prevents conflicts when production only has one subject

**Which Script to Use:**

| Scenario | Script to Use |
|----------|--------------|
| Production has only Maths | `sync_maths_only_to_production.sh` |
| Production has only Physics | `sync_physics_only_to_production.sh` |
| Production has both subjects | `sync_to_production_simple.sh` |
| Adding new Maths questions only | `sync_maths_only_to_production.sh` |
| Adding new Physics questions only | `sync_physics_only_to_production.sh` |

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

### Import Fails with "Duplicate entry 'differentiation'" Error
**Cause:** Using `loaddata` on existing topics/sections
**Symptom:** `IntegrityError: (1062, "Duplicate entry 'differentiation' for key 'interactive_lessons_topic.slug'")`
**Fix:** Use `import_questions_safe` instead of `loaddata` (see "Questions (Safe Import/Export)" section above)

### Import Fails with "QuestionPart() got unexpected keyword arguments: 'hint'"
**Cause:** `import_questions_safe` command is outdated
**Fix:**
```bash
# On PythonAnywhere
git pull origin main  # Get latest import command
python manage.py import_questions_safe your_file.json
```

### Import Fails with IntegrityError (Other)
**Cause:** Data already exists or constraint violation
**Fix:** Check error message for specific field causing conflict

### Import Fails with Schema Error
**Cause:** Migrations not run
**Fix:** `python manage.py migrate`

### Changes Not Visible
**Cause:** Web app not reloaded
**Fix:** `touch /var/www/morgan360_pythonanywhere_com_wsgi.py`

### Large Import Times Out
**Cause:** Normal for large datasets
**Fix:** Be patient, imports can take 30-60 seconds

### --exclude Flag Doesn't Work with loaddata
**Cause:** Foreign key references are resolved before exclusion
**Fix:** Use `import_questions_safe` instead, which properly handles existing relationships

---

## Quick Command Summary

| Task | Command |
|------|---------|
| Export Maths (merge) | `./deployment/sync_maths_only_to_production.sh` |
| Export Maths (replace) | `./deployment/sync_maths_replace_production.sh` |
| Export Physics only | `./deployment/sync_physics_only_to_production.sh` |
| Export all subjects | `./deployment/sync_to_production_simple.sh` |
| Export questions (safe) | `./deployment/sync_questions_safe.sh` |
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
