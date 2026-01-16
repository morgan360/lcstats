# Deploy Django Groups to Live Production Server

## Pre-Deployment: Commit Code First

**IMPORTANT:** Commit and push your code BEFORE deploying to live:

```bash
# On your LOCAL machine (macOS)
git add students/migrations/0008_setup_user_groups.py
git add students/decorators.py
git add students/signals.py
git add homework/views.py
git commit -m "Add Django Groups for student/teacher permissions"
git push origin main
```

---

## Production Server Deployment

### Step 1: SSH to Production
```bash
ssh your-production-server
# or whatever your SSH command is
```

### Step 2: Backup Database

If you got the socket error, your production server might be configured differently. Try these in order:

**Option A: Standard MySQL backup**
```bash
mysqldump -u morgan -p lcaim > backup_before_groups_$(date +%Y%m%d_%H%M%S).sql
# Enter password when prompted: help1234
```

**Option B: If socket error, use TCP/IP**
```bash
mysqldump -h 127.0.0.1 -u morgan -p lcaim > backup_before_groups_$(date +%Y%m%d_%H%M%S).sql
# Enter password when prompted: help1234
```

**Option C: If MySQL on different host**
```bash
mysqldump -h localhost -u morgan -p lcaim > backup_before_groups_$(date +%Y%m%d_%H%M%S).sql
# Enter password when prompted: help1234
```

**Option D: Check MySQL configuration**
```bash
# Find MySQL socket location
mysql_config --socket
# or
sudo find / -name "mysql.sock" 2>/dev/null

# Then use the socket path:
mysqldump --socket=/path/to/mysql.sock -u morgan -p lcaim > backup_before_groups_$(date +%Y%m%d_%H%M%S).sql
```

**Option E: If MySQL is running via Docker/systemd**
```bash
# Check if MySQL is running
systemctl status mysql
# or
systemctl status mariadb

# If not running, start it:
sudo systemctl start mysql
```

### Step 3: Verify Backup Created
```bash
ls -lh backup_before_groups_*.sql
# Should see a file with today's date and reasonable size (> 1MB)
```

### Step 4: Navigate to Project
```bash
cd /path/to/lcstats
# Replace with your actual project path, e.g.:
# cd /var/www/lcstats
# cd /home/morgan/lcstats
# cd ~/lcstats
```

### Step 5: Pull Latest Code
```bash
git pull origin main
```

### Step 6: Activate Virtual Environment
```bash
# Try one of these (depends on your setup):
source venv/bin/activate
# or
source env/bin/activate
# or
source .venv/bin/activate
```

### Step 7: Run Migration
```bash
python manage.py migrate students

# Expected output:
# Operations to perform:
#   Apply all migrations: students
# Running migrations:
#   Applying students.0008_setup_user_groups... OK
```

### Step 8: Verify Migration
```bash
python manage.py shell -c "
from django.contrib.auth.models import Group, User
groups = Group.objects.all()
print('Groups created:')
for g in groups:
    print(f'  {g.name}: {g.user_set.count()} users')
"
```

Expected output:
```
Groups created:
  Students: X users
  Teachers: Y users
```

### Step 9: Collect Static Files (if needed)
```bash
python manage.py collectstatic --noinput
```

### Step 10: Restart Application

Choose the command that matches your setup:

**Systemd service:**
```bash
sudo systemctl restart lcstats
# or
sudo systemctl restart gunicorn
```

**Supervisor:**
```bash
sudo supervisorctl restart lcstats
```

**Apache:**
```bash
sudo service apache2 restart
# or
sudo systemctl restart apache2
```

**Nginx + Gunicorn:**
```bash
sudo systemctl restart gunicorn
sudo systemctl restart nginx
```

**Direct Gunicorn:**
```bash
pkill gunicorn
gunicorn lcstats.wsgi:application --bind 0.0.0.0:8000 --daemon
```

### Step 11: Check Logs
```bash
# Django logs (location varies)
tail -f /var/log/lcstats/error.log

# Systemd logs
sudo journalctl -u lcstats -f

# Apache logs
tail -f /var/log/apache2/error.log

# Nginx logs
tail -f /var/log/nginx/error.log
```

### Step 12: Test Live Site

1. **Test Teacher Access:**
   - Login as a teacher
   - Visit: `https://your-domain.com/homework/teacher/`
   - Should see teacher dashboard ✓

2. **Test Student Access:**
   - Login as a student
   - Visit: `https://your-domain.com/homework/teacher/`
   - Should get "Permission Denied" ✓
   - Visit: `https://your-domain.com/homework/`
   - Should see student homework dashboard ✓

3. **Test New User Registration:**
   - Create a new student account
   - Check in Django admin that they're in "Students" group

---

## Troubleshooting

### Issue: Can't connect to MySQL socket

**Solution 1: Check if MySQL is running**
```bash
sudo systemctl status mysql
sudo systemctl start mysql  # if not running
```

**Solution 2: Use TCP/IP instead of socket**
```bash
mysqldump -h 127.0.0.1 -u morgan -p lcaim > backup.sql
```

**Solution 3: Find correct socket**
```bash
mysql_config --socket
# Use the path shown:
mysqldump --socket=/var/run/mysqld/mysqld.sock -u morgan -p lcaim > backup.sql
```

### Issue: Permission denied during backup

**Solution:**
```bash
# Make sure you have write permissions in current directory
cd ~
mysqldump -u morgan -p lcaim > backup_before_groups_$(date +%Y%m%d_%H%M%S).sql
```

### Issue: Migration fails

**Solution: Rollback**
```bash
python manage.py migrate students 0007
```

Then restore backup:
```bash
mysql -u morgan -p lcaim < backup_before_groups_YYYYMMDD_HHMMSS.sql
```

### Issue: Users can't access pages after deployment

**Check user groups:**
```bash
python manage.py shell
>>> from django.contrib.auth.models import User
>>> user = User.objects.get(username='problematic_username')
>>> print(user.groups.all())
>>> print(user.is_staff)
```

**Manually assign to group:**
```bash
python manage.py shell
>>> from django.contrib.auth.models import User, Group
>>> user = User.objects.get(username='username')
>>> group = Group.objects.get(name='Students')  # or 'Teachers'
>>> user.groups.add(group)
```

---

## Rollback Procedure

If anything goes wrong:

```bash
# 1. Rollback migration
cd /path/to/lcstats
source venv/bin/activate
python manage.py migrate students 0007

# 2. Restart application
sudo systemctl restart lcstats

# 3. (Optional) Restore database from backup
mysql -u morgan -p lcaim < backup_before_groups_YYYYMMDD_HHMMSS.sql

# 4. Restart application again
sudo systemctl restart lcstats
```

---

## Quick Reference

### Most Common Deployment Flow
```bash
# 1. SSH to production
ssh production-server

# 2. Backup
cd ~
mysqldump -h 127.0.0.1 -u morgan -p lcaim > backup_$(date +%Y%m%d_%H%M%S).sql

# 3. Deploy
cd /path/to/lcstats
git pull origin main
source venv/bin/activate
python manage.py migrate students
python manage.py collectstatic --noinput
sudo systemctl restart lcstats

# 4. Verify
tail -f /var/log/lcstats/error.log
```

### Files Changed (for reference)
- `students/migrations/0008_setup_user_groups.py`
- `students/decorators.py`
- `students/signals.py`
- `homework/views.py`

---

## After Deployment

Monitor for 24-48 hours:
- Check error logs daily
- Verify no permission errors
- Confirm new registrations work
- Test both student and teacher logins

**Backup is safe to keep indefinitely** - stores full database state before migration.