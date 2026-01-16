# Quick Deployment Guide - Django Groups

## ✅ Pre-Deployment Status
All tests passed locally. Safe to deploy to production.

## Fast Track (5 minutes)

### 1. Commit and Push (Local)
```bash
git add students/migrations/0008_setup_user_groups.py
git add students/decorators.py
git add students/signals.py
git add homework/views.py
git add DEPLOYMENT_GROUPS.md
git add deploy_groups.sh
git add test_groups.py
git commit -m "Add Django Groups for student/teacher permissions"
git push origin main
```

### 2. Backup Database (Production)
```bash
ssh your-production-server
mysqldump -u morgan -p lcaim > backup_groups_$(date +%Y%m%d_%H%M%S).sql
```

### 3. Deploy (Production)
```bash
cd /path/to/lcstats
git pull origin main
source venv/bin/activate  # or source env/bin/activate
python manage.py migrate students
python manage.py collectstatic --noinput

# Restart your app (choose one):
sudo systemctl restart lcstats           # systemd
sudo supervisorctl restart lcstats        # supervisor
sudo service apache2 restart              # Apache
sudo service gunicorn restart             # Gunicorn service
```

### 4. Verify (Production)
```bash
python manage.py shell -c "
from django.contrib.auth.models import Group
print('Groups:', [(g.name, g.user_set.count()) for g in Group.objects.all()])
"
```

Expected output:
```
Groups: [('Students', X), ('Teachers', Y)]
```

### 5. Test Manually
- Login as teacher → Visit `/homework/teacher/` → Should work ✓
- Login as student → Visit `/homework/teacher/` → Should get permission denied ✓
- Create new user with student code → Check they're in Students group ✓

## If Something Goes Wrong

### Quick Rollback
```bash
cd /path/to/lcstats
source venv/bin/activate
python manage.py migrate students 0007
sudo systemctl restart lcstats  # or your restart command
```

### Restore Database
```bash
mysql -u morgan -p lcaim < backup_groups_YYYYMMDD_HHMMSS.sql
```

## What Changed
- ✅ New groups: Students, Teachers
- ✅ All existing users assigned to groups
- ✅ New users auto-assigned on registration
- ✅ Permission decorators for views
- ✅ No breaking changes (backward compatible)

## Support
See `DEPLOYMENT_GROUPS.md` for detailed documentation.

## Files Modified
- `students/migrations/0008_setup_user_groups.py` (new)
- `students/decorators.py` (new)
- `students/signals.py` (updated)
- `homework/views.py` (updated)