# Database Sync Guide

Simple guide for syncing your databases between local development and production (PythonAnywhere).

---

## Quick Sync to Production (Recommended)

### Script: `sync_to_production_simple.sh`

**When to use:**
- After adding/editing questions locally
- After creating new topics
- After adding/updating notes

**Steps:**

1. **Run the sync script:**
   ```bash
   ./sync_to_production_simple.sh
   ```

2. **SSH to PythonAnywhere and import:**
   The script will show you the exact commands to run. Copy and paste them:
   ```bash
   ssh morganmck@ssh.eu.pythonanywhere.com
   cd ~/lcstats
   source venv/bin/activate
   python manage.py loaddata questions_YYYYMMDD_HHMMSS.json
   python manage.py loaddata notes_YYYYMMDD_HHMMSS.json
   exit
   ```

3. **Reload your web app:**
   - Go to: https://eu.pythonanywhere.com/user/morganmck/webapps/
   - Click the **Reload** button (green button with circular arrow)

**That's it!** Your changes are now live.

---

## What Gets Synced

### ✅ Synced:
- Topics
- Questions
- Question Parts
- Notes

### ❌ NOT Synced (stays separate on each environment):
- Student data (StudentProfile, QuestionAttempt)
- User accounts
- InfoBot query history
- Admin logs

---

## Manual Export/Import Commands

If you prefer to do things manually or need more control:

### Export from Local:
```bash
# Export questions
python manage.py dumpdata interactive_lessons.Topic interactive_lessons.Question interactive_lessons.QuestionPart \
    --indent 2 > questions.json

# Export notes
python manage.py dumpdata notes.Note --indent 2 > notes.json
```

### Upload to PythonAnywhere:
```bash
scp questions.json morganmck@ssh.eu.pythonanywhere.com:~/lcstats/
scp notes.json morganmck@ssh.eu.pythonanywhere.com:~/lcstats/
```

### Import on PythonAnywhere:
```bash
ssh morganmck@ssh.eu.pythonanywhere.com
cd ~/lcstats
source venv/bin/activate
python manage.py loaddata questions.json
python manage.py loaddata notes.json
exit
```

### Reload Web App:
https://eu.pythonanywhere.com/user/morganmck/webapps/

---

## Recommended Workflow

### Daily Development:
1. Work locally at http://127.0.0.1:8000/admin/
2. Add/edit questions and test thoroughly
3. Run `./sync_to_production_simple.sh`
4. Follow the displayed commands to import on PythonAnywhere
5. Reload web app

### Quick Typo Fixes:
- Small fixes can be done directly on production admin
- For multiple changes, always work locally first

---

## Troubleshooting

**"Permission denied" when running script:**
```bash
chmod +x sync_to_production_simple.sh
```

**"Connection refused" or password error:**
- Check your PythonAnywhere password hasn't expired
- Try logging in at https://www.pythonanywhere.com

**"Primary key already exists" error:**
- This is normal! Django's loaddata updates existing records by primary key
- New items are added, existing ones are updated

**Import seems stuck:**
- Large files can take 30-60 seconds to import
- Wait for the command prompt to return
- Check for error messages

**Changes don't appear on live site:**
- Did you reload the web app? (Most common issue!)
- Check you imported the correct timestamped file
- Check Django admin on production to verify data

---

## Backup Files

Each sync creates timestamped backup files:
- `questions_20251116_195832.json`
- `notes_20251116_195832.json`

**Keep these files!** They're your safety net.

To restore from backup:
```bash
python manage.py loaddata questions_20251116_195832.json
```

---

## Advanced: Pull from Production (Reverse Sync)

If you made changes on production and want to bring them back to local:

### On PythonAnywhere:
```bash
ssh morganmck@ssh.eu.pythonanywhere.com
cd ~/lcstats
source venv/bin/activate
python manage.py dumpdata interactive_lessons.Topic interactive_lessons.Question interactive_lessons.QuestionPart --indent 2 > questions_prod.json
python manage.py dumpdata notes.Note --indent 2 > notes_prod.json
exit
```

### Download to Local:
```bash
scp morganmck@ssh.eu.pythonanywhere.com:~/lcstats/questions_prod.json .
scp morganmck@ssh.eu.pythonanywhere.com:~/lcstats/notes_prod.json .
```

### Import Locally:
```bash
python manage.py loaddata questions_prod.json
python manage.py loaddata notes_prod.json
```

⚠️ **WARNING:** This overwrites your local database with production data!

---

## Quick Reference

### Sync to Production:
```bash
./sync_to_production_simple.sh
# Then follow displayed commands
```

### Check what will be synced:
```bash
python manage.py dumpdata interactive_lessons.Question --indent 2 | grep '"order"'
```

### Reload Web App:
https://eu.pythonanywhere.com/user/morganmck/webapps/

### View Logs on PythonAnywhere:
- Go to Web tab
- Scroll to "Log files"
- Check error.log and server.log

---

## Need Help?

1. Check the error message carefully
2. Look at backup files created (they have timestamps)
3. Check PythonAnywhere error logs
4. Try the manual export/import commands above
5. You can always restore from backup files
