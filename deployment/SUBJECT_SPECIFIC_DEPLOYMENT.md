# Subject-Specific Deployment Guide

## Overview

This guide explains how to deploy **Maths** and **Physics** data separately to production using subject-specific deployment scripts.

## Why Subject-Specific Deployment?

Your local database contains:
- **19 Maths topics** with 495 questions (697 question parts)
- **11 Physics topics** with 1 question (4 question parts)

If your production server only has one subject configured, using the standard deployment script will cause **foreign key errors** when it tries to reference a Subject that doesn't exist.

## Deployment Scripts

### 📊 Comparison Table

| Script | Topics | Sections | Questions | Parts | Use When |
|--------|--------|----------|-----------|-------|----------|
| `sync_maths_only_to_production.sh` | 19 | 175 | 495 | 697 | Production has only Maths |
| `sync_physics_only_to_production.sh` | 11 | 1 | 1 | 4 | Production has only Physics |
| `sync_to_production_simple.sh` | 30 | 176 | 496 | 701 | Production has both subjects |

---

## 🔢 Deploy Maths Only

**Use this when your production server only has the Maths subject configured.**

### Step 1: Export Maths Data Locally

```bash
cd ~/lcstats
./deployment/sync_maths_only_to_production.sh
```

This creates 5 files:
- `maths_topics_YYYYMMDD_HHMMSS.json` (19 Maths topics)
- `maths_sections_YYYYMMDD_HHMMSS.json` (175 sections)
- `maths_questions_YYYYMMDD_HHMMSS.json` (495 questions)
- `maths_parts_YYYYMMDD_HHMMSS.json` (697 question parts)
- `maths_notes_YYYYMMDD_HHMMSS.json` (5 notes)

### Step 2: Upload to PythonAnywhere

1. Go to: https://www.pythonanywhere.com/user/morganmck/files/home/morganmck/lcstats/
2. Click "Upload a file"
3. Upload all 5 `maths_*.json` files

### Step 3: Import on PythonAnywhere

Open a Bash console and run:

```bash
cd ~/lcstats
source venv/bin/activate

# Import in this order (important!)
python manage.py loaddata maths_topics_YYYYMMDD_HHMMSS.json
python manage.py loaddata maths_sections_YYYYMMDD_HHMMSS.json
python manage.py loaddata maths_questions_YYYYMMDD_HHMMSS.json
python manage.py loaddata maths_parts_YYYYMMDD_HHMMSS.json
python manage.py loaddata maths_notes_YYYYMMDD_HHMMSS.json

# Reload web app
touch /var/www/morganmck_eu_pythonanywhere_com_wsgi.py
```

### Step 4: Verify

Visit your site and check:
- Complex Numbers topic has new sections
- New questions are visible
- All questions display correctly

---

## ⚛️ Deploy Physics Only

**Use this when your production server only has the Physics subject configured.**

### Step 1: Export Physics Data Locally

```bash
cd ~/lcstats
./deployment/sync_physics_only_to_production.sh
```

This creates 5 files:
- `physics_topics_YYYYMMDD_HHMMSS.json` (11 Physics topics)
- `physics_sections_YYYYMMDD_HHMMSS.json` (1 section)
- `physics_questions_YYYYMMDD_HHMMSS.json` (1 question)
- `physics_parts_YYYYMMDD_HHMMSS.json` (4 question parts)
- `physics_notes_YYYYMMDD_HHMMSS.json` (0 notes)

### Step 2: Upload to PythonAnywhere

1. Go to: https://www.pythonanywhere.com/user/morganmck/files/home/morganmck/lcstats/
2. Click "Upload a file"
3. Upload all 5 `physics_*.json` files

### Step 3: Import on PythonAnywhere

Open a Bash console and run:

```bash
cd ~/lcstats
source venv/bin/activate

# Import in this order (important!)
python manage.py loaddata physics_topics_YYYYMMDD_HHMMSS.json
python manage.py loaddata physics_sections_YYYYMMDD_HHMMSS.json
python manage.py loaddata physics_questions_YYYYMMDD_HHMMSS.json
python manage.py loaddata physics_parts_YYYYMMDD_HHMMSS.json
python manage.py loaddata physics_notes_YYYYMMDD_HHMMSS.json

# Reload web app
touch /var/www/morganmck_eu_pythonanywhere_com_wsgi.py
```

---

## 📚 Deploy Both Subjects

**Use this when your production server has BOTH Maths and Physics subjects configured.**

### Step 1: Export All Data

```bash
cd ~/lcstats
./deployment/sync_to_production_simple.sh
```

This creates 2 files with ALL data:
- `questions_YYYYMMDD_HHMMSS.json` (all topics, sections, questions, parts)
- `notes_YYYYMMDD_HHMMSS.json` (all notes)

### Step 2: Upload and Import

Follow the standard deployment process (see `IMPORT_EXPORT_COMMANDS.md`).

---

## 🆕 What's New in This Export

The Maths export includes **12 new Complex Numbers questions** across 4 new sections:

### 1. Polar Form of Complex Numbers (3 questions)
- ID 533: Convert $-1 + \sqrt{3}i$ to polar form
- ID 534: Convert $-3 - 3i$ to polar form
- ID 535: Convert $2 - 2\sqrt{3}i$ to polar form
- All include Argand diagrams

### 2. Division and Multiplication with Polar Form (3 questions)
- ID 536: Multiply/divide polar form complex numbers
- ID 537: Operations with different quadrant angles
- ID 538: Find unknown complex number from product

### 3. Applications of De Moivre's Theorem (3 questions)
- ID 539: $(1 + i)^{10}$ using De Moivre's Theorem
- ID 540: $(\sqrt{3} - i)^6$ using De Moivre's Theorem
- ID 541: Prove $\cos 3\theta = 4\cos^3\theta - 3\cos\theta$

### 4. Finding the Roots of Complex Numbers (3 questions)
- ID 542: Fourth roots of $8i$ (with Argand diagram)
- ID 543: Cube roots of $-1 - \sqrt{3}i$ (with Argand diagram)
- ID 544: Fourth roots of $-16$ in rectangular form

---

## 🔍 Troubleshooting

### Error: "Cannot resolve keyword 'subject'"
**Cause:** Production database doesn't have the `core` app or `Subject` model migrated.
**Fix:** Run migrations on production:
```bash
python manage.py migrate core
```

### Error: "Subject matching query does not exist"
**Cause:** Using wrong deployment script (e.g., trying to import Physics when only Maths subject exists).
**Fix:** Use the correct subject-specific script.

### Error: "Duplicate entry for key 'slug'"
**Cause:** Topics already exist in production.
**Fix:** This is expected behavior. The script will update existing topics. If you get this error, it means the import partially succeeded. Check which data imported successfully.

---

## 📖 Full Documentation

For complete deployment documentation, see:
- `docs/IMPORT_EXPORT_COMMANDS.md` - All import/export commands
- `deployment/DEPLOYMENT_NOTES.md` - General deployment notes
- `deployment/sync_maths_only_to_production.sh` - Maths deployment script
- `deployment/sync_physics_only_to_production.sh` - Physics deployment script

---

## 🎯 Quick Reference

| Your Production Has | Script to Use |
|-------------------|---------------|
| Only Maths subject | `sync_maths_only_to_production.sh` |
| Only Physics subject | `sync_physics_only_to_production.sh` |
| Both subjects | `sync_to_production_simple.sh` |
| Unsure | Use `sync_maths_only_to_production.sh` (safest option) |

**Remember:** Always reload the web app after importing!
```bash
touch /var/www/morganmck_eu_pythonanywhere_com_wsgi.py
```
