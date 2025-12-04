# Manual Database Sync to PythonAnywhere
- ./sync_to_production_simple.sh
- python manage.py loaddata questions_YYYYMMDD_HHMMSS.json



This guide covers the manual process for syncing your local database changes to PythonAnywhere production when SSH/SCP is unavailable.

## When to Use This Guide

Use this manual process when:
- SSH connections to PythonAnywhere timeout
- The automatic `sync_to_production_simple.sh` script fails
- You're working from a network that blocks SSH port 22

## Prerequisites

- Local development database with changes to sync
- Access to PythonAnywhere web dashboard
- PythonAnywhere account credentials

## Step-by-Step Process

### Step 1: Export Local Database

From your local `lcstats` directory, run:

```bash
./sync_to_production_simple.sh
```

Or manually export with:

```bash
# Set timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Export questions, sections, and topics
python manage.py dumpdata interactive_lessons.Topic interactive_lessons.Section interactive_lessons.Question interactive_lessons.QuestionPart \
    --indent 2 > questions_${TIMESTAMP}.json

# Export notes
python manage.py dumpdata notes.Note \
    --indent 2 > notes_${TIMESTAMP}.json
```

This creates two files:
- `questions_YYYYMMDD_HHMMSS.json`
- `notes_YYYYMMDD_HHMMSS.json`

### Step 2: Upload Files to PythonAnywhere

#### Via Web Dashboard

1. Go to PythonAnywhere Files page:
   ```
   https://www.pythonanywhere.com/user/morganmck/files/home/morganmck/lcstats/
   ```

2. Click the **"Upload a file"** button

3. Upload both files:
   - `questions_YYYYMMDD_HHMMSS.json`
   - `notes_YYYYMMDD_HHMMSS.json`

4. Verify files appear in the `~/lcstats/` directory listing

### Step 3: Import Data on PythonAnywhere

1. Open a Bash console on PythonAnywhere:
   ```
   https://www.pythonanywhere.com/user/morganmck/consoles/
   ```

2. Click **"Bash"** to start a new console

3. Run the import commands (replace `YYYYMMDD_HHMMSS` with your timestamp):

```bash
# Navigate to project directory
cd ~/lcstats

# Activate virtual environment
source venv/bin/activate

# Import questions (this may take 30-60 seconds)
python manage.py loaddata questions_YYYYMMDD_HHMMSS.json

# Import notes (this may take 30-60 seconds)
python manage.py loaddata notes_YYYYMMDD_HHMMSS.json

# Reload web app by touching WSGI file
touch /var/www/morganmck_eu_pythonanywhere_com_wsgi.py

# Confirm completion
echo "Import complete! Web app reloaded."
```

### Step 4: Verify Changes

1. Visit your site: `https://morganmck.eu.pythonanywhere.com`

2. Log in to the admin: `https://morganmck.eu.pythonanywhere.com/admin/`

3. Navigate to **Interactive Lessons → Questions**

4. Verify new questions are present

## Expected Output

When importing, you should see output like:

```
Installed 160 object(s) from 1 fixture(s)
```

This indicates the number of database records imported.

## Troubleshooting

### "Could not load interactive_lessons.Question"

**Issue:** Database schema mismatch

**Solution:** Run migrations first:
```bash
python manage.py migrate
```

### "IntegrityError: Duplicate entry"

**Issue:** Data already exists in database

**Solution:** The data is already imported. You can safely ignore this or check for newer exports.

### Import Takes Too Long

**Issue:** Large dataset causing timeout

**Solution:** Import is working, just be patient. Questions file typically takes 30-60 seconds.

### Changes Not Visible After Import

**Issue:** Web app not reloaded

**Solution:** Touch the WSGI file again:
```bash
touch /var/www/morganmck_eu_pythonanywhere_com_wsgi.py
```

Or use the "Reload" button in the Web tab:
```
https://eu.pythonanywhere.com/user/morganmck/webapps/
```

## Cleanup (Optional)

After successful import, you can delete the JSON files to save space:

```bash
cd ~/lcstats
rm questions_YYYYMMDD_HHMMSS.json
rm notes_YYYYMMDD_HHMMSS.json
```

## What Gets Synced

This process syncs:
- ✅ Topics
- ✅ Sections (within topics)
- ✅ Questions (all question data)
- ✅ Question Parts (sub-questions, answers, solutions)
- ✅ Notes (RAG knowledge base)

This process does NOT sync:
- ❌ Student data (StudentProfile, QuestionAttempt)
- ❌ User accounts
- ❌ Registration codes
- ❌ Login history
- ❌ Static files or code changes

**Important Note on Deletions:**
- This sync process only ADDS or UPDATES data
- If you delete a Topic/Section/Question locally, it will NOT be deleted in production
- To delete in production: manually delete via admin interface or Django shell

## Alternative: Code Changes

For code changes (like the new PDF reports in `students/admin.py`), you need to:

1. Commit and push changes to GitHub
2. Pull on PythonAnywhere:
   ```bash
   cd ~/lcstats
   git pull origin main
   ```
3. Reload web app:
   ```bash
   touch /var/www/morganmck_eu_pythonanywhere_com_wsgi.py
   ```

## Summary Command Reference

```bash
# LOCAL: Export data
./sync_to_production_simple.sh

# PYTHONANYWHERE: Import data
cd ~/lcstats
source venv/bin/activate
python manage.py loaddata questions_YYYYMMDD_HHMMSS.json
python manage.py loaddata notes_YYYYMMDD_HHMMSS.json
touch /var/www/morganmck_eu_pythonanywhere_com_wsgi.py
```

## Need Help?

- PythonAnywhere Help: https://help.pythonanywhere.com/
- PythonAnywhere Forums: https://www.pythonanywhere.com/forums/
- Django loaddata docs: https://docs.djangoproject.com/en/stable/ref/django-admin/#loaddata