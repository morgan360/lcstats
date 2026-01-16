# Deploy Django Groups to PythonAnywhere

## PythonAnywhere-Specific Deployment Guide

PythonAnywhere has different MySQL access than standard servers. Follow these steps:

---

## Step 1: Backup Database on PythonAnywhere

PythonAnywhere MySQL needs the full hostname. Your MySQL hostname is typically:
`username.mysql.pythonanywhere-services.com`

### Find Your MySQL Hostname:
1. Go to PythonAnywhere Dashboard → **Databases** tab
2. Look for "MySQL hostname" - it will be something like:
   - `morgan.mysql.pythonanywhere-services.com`
   - Or check your Django settings.py for the DATABASES host

### Create Backup:

```bash
# On PythonAnywhere console
cd ~/lcstats

# Use your PythonAnywhere MySQL hostname
mysqldump -h YOUR-USERNAME.mysql.pythonanywhere-services.com -u YOUR-USERNAME -p lcaim > backup_before_groups_$(date +%Y%m%d_%H%M%S).sql

# Example (replace 'morgan' with your username):
mysqldump -h morgan.mysql.pythonanywhere-services.com -u morgan -p lcaim > backup_before_groups_$(date +%Y%m%d_%H%M%S).sql
```

When prompted, enter your **PythonAnywhere MySQL password** (might be different from 'help1234').

### Verify Backup:
```bash
ls -lh backup_before_groups_*.sql
# Should show a file > 100KB
```

---

## Step 2: Pull Latest Code

```bash
cd ~/lcstats
git pull origin main
```

**FIRST:** Make sure you've committed and pushed from your local machine:
```bash
# On your LOCAL macOS machine:
git add students/migrations/0008_setup_user_groups.py
git add students/decorators.py
git add students/signals.py
git add homework/views.py
git commit -m "Add Django Groups for student/teacher permissions"
git push origin main
```

---

## Step 3: Activate Virtual Environment

```bash
# PythonAnywhere typically uses:
workon your-virtualenv-name

# Or if you have a standard venv:
source venv/bin/activate
# or
source .virtualenvs/your-env-name/bin/activate
```

**To find your virtualenv name:**
- Check PythonAnywhere Dashboard → **Web** tab
- Look at the "Virtualenv" section
- Or run: `ls ~/.virtualenvs/`

---

## Step 4: Run Migration

```bash
cd ~/lcstats
python manage.py migrate students
```

Expected output:
```
Operations to perform:
  Apply all migrations: students
Running migrations:
  Applying students.0008_setup_user_groups... OK
```

---

## Step 5: Verify Groups Created

```bash
python manage.py shell -c "
from django.contrib.auth.models import Group, User
print('=== Groups Created ===')
for g in Group.objects.all():
    print(f'{g.name}: {g.user_set.count()} users')
print('\n=== Sample Users ===')
for u in User.objects.all()[:5]:
    groups = ', '.join([g.name for g in u.groups.all()])
    print(f'{u.username} (staff={u.is_staff}): {groups}')
"
```

---

## Step 6: Collect Static Files

```bash
python manage.py collectstatic --noinput
```

---

## Step 7: Reload Web App

### Option A: Via Web Interface (Recommended)
1. Go to PythonAnywhere Dashboard
2. Click **Web** tab
3. Click the big green **Reload** button for your domain

### Option B: Via Command Line
```bash
# Use the PythonAnywhere API (if you have API token)
pa_reload_webapp.py your-username.pythonanywhere.com
```

### Option C: Via Touch WSGI
```bash
# Touch the WSGI file to reload
touch /var/www/your-username_pythonanywhere_com_wsgi.py
```

---

## Step 8: Check Error Logs

```bash
# PythonAnywhere error log location:
tail -f ~/lcstats/error.log

# Or check via Dashboard:
# Web tab → Log files section → error.log
```

---

## Step 9: Test Live Site

1. Visit your PythonAnywhere site: `https://your-username.pythonanywhere.com`

2. **Test Teacher Access:**
   - Login as teacher
   - Go to `/homework/teacher/`
   - Should see teacher dashboard ✓

3. **Test Student Access:**
   - Login as student
   - Try `/homework/teacher/`
   - Should get "Permission Denied" ✓

---

## Troubleshooting

### Issue: Can't find MySQL hostname

**Solution:**
```bash
# Check your Django settings
cat ~/lcstats/lcstats/settings.py | grep -A 5 DATABASES

# Or check environment variables
cat ~/lcstats/.env | grep DATABASE
```

The hostname is in the `DATABASES['default']['HOST']` setting.

### Issue: MySQL password wrong

**Solutions:**
1. Check your `.env` file for the correct password
2. Or check PythonAnywhere Dashboard → **Databases** tab
3. Reset MySQL password if needed (on Databases tab)

### Issue: Migration already applied

This is fine! Just means it was already run. Verify groups exist:
```bash
python manage.py shell -c "from django.contrib.auth.models import Group; print(list(Group.objects.values_list('name', flat=True)))"
```

### Issue: Web app won't reload

**Solutions:**
1. Check error log: `tail -50 ~/lcstats/error.log`
2. Check WSGI file syntax: `python -m py_compile /var/www/your-username_pythonanywhere_com_wsgi.py`
3. Reload manually via Web tab

### Issue: Import error for decorators

**Solution:**
```bash
# Make sure all files are committed and pulled
cd ~/lcstats
git status
git pull origin main

# Verify file exists
ls -la students/decorators.py
```

---

## Quick Reference - PythonAnywhere Deployment

```bash
# === On LOCAL machine (macOS) FIRST ===
git add students/migrations/0008_setup_user_groups.py students/decorators.py students/signals.py homework/views.py
git commit -m "Add Django Groups for permissions"
git push origin main

# === Then on PythonAnywhere console ===
cd ~/lcstats

# Backup (replace 'morgan' with your username)
mysqldump -h morgan.mysql.pythonanywhere-services.com -u morgan -p lcaim > backup_$(date +%Y%m%d_%H%M%S).sql

# Deploy
git pull origin main
workon your-virtualenv-name  # or source venv/bin/activate
python manage.py migrate students
python manage.py collectstatic --noinput

# Reload via Web tab or:
touch /var/www/your-username_pythonanywhere_com_wsgi.py

# Check logs
tail -f ~/lcstats/error.log
```

---

## Rollback on PythonAnywhere

If something goes wrong:

```bash
cd ~/lcstats
workon your-virtualenv-name

# Rollback migration
python manage.py migrate students 0007

# Restore database
mysql -h morgan.mysql.pythonanywhere-services.com -u morgan -p lcaim < backup_before_groups_YYYYMMDD_HHMMSS.sql

# Reload web app
# Go to Web tab → Click Reload button
```

---

## Important PythonAnywhere Notes

1. **MySQL Hostname:** Always use full hostname: `username.mysql.pythonanywhere-services.com`
2. **Can't use localhost or 127.0.0.1** - PythonAnywhere MySQL is on a separate server
3. **Reload required:** Always reload web app after code/migration changes
4. **Virtual env:** Make sure you activate the correct virtualenv
5. **File paths:** Everything under `/home/username/` directory

---

## Finding Your Settings

### MySQL Hostname:
```bash
grep "HOST" ~/lcstats/lcstats/settings.py
# or
grep "mysql" ~/lcstats/.env
```

### Virtualenv Name:
- Check Web tab on PythonAnywhere Dashboard
- Or: `ls ~/.virtualenvs/`

### WSGI File Location:
- Usually: `/var/www/username_pythonanywhere_com_wsgi.py`
- Check Web tab → Code section → WSGI configuration file

---

## Success Checklist

✅ Backup created successfully
✅ Code pulled from git
✅ Migration applied without errors
✅ Groups visible in shell check
✅ Static files collected
✅ Web app reloaded
✅ No errors in log
✅ Teacher can access teacher views
✅ Student cannot access teacher views

**You're done!** Monitor for 24 hours and check error logs.