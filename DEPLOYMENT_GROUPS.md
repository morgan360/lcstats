# Django Groups Migration - Production Deployment Guide

## Overview
This deployment adds Django Groups for student and teacher permission management.

**Risk Level**: Low (backward compatible, includes rollback)

## Files Changed
1. `students/migrations/0008_setup_user_groups.py` - New migration
2. `students/decorators.py` - New file with permission decorators
3. `students/signals.py` - Updated to auto-assign groups
4. `homework/views.py` - Updated to use new decorators

## Pre-Deployment Checklist

### 1. Backup Database
```bash
# SSH into production server
ssh your-server

# Backup MySQL database
mysqldump -u morgan -p lcaim > backup_before_groups_$(date +%Y%m%d_%H%M%S).sql
```

### 2. Test Migration Locally
✅ Already tested - rollback confirmed working

### 3. Review Changes
```bash
git diff main
```

## Deployment Steps

### Step 1: Commit Changes to Git
```bash
# On local machine
git add students/migrations/0008_setup_user_groups.py
git add students/decorators.py
git add students/signals.py
git add homework/views.py
git commit -m "Add Django Groups for student/teacher permissions

- Create Students and Teachers groups
- Auto-assign users to groups on registration
- Add permission decorators for view protection
- Update homework views to use group-based permissions
- Migration assigns existing users to appropriate groups"
git push origin main
```

### Step 2: Deploy to Production
```bash
# SSH into production server
ssh your-server

# Navigate to project directory
cd /path/to/lcstats

# Pull latest changes
git pull origin main

# Activate virtual environment
source venv/bin/activate

# Run migrations (this creates groups and assigns existing users)
python manage.py migrate students

# Restart application server (adjust based on your setup)
# If using systemd:
sudo systemctl restart lcstats

# If using Gunicorn directly:
sudo supervisorctl restart lcstats

# If using Apache/mod_wsgi:
sudo service apache2 restart
```

### Step 3: Verify Deployment
```bash
# Check groups were created
python manage.py shell -c "
from django.contrib.auth.models import Group, User
print('Groups:', [(g.name, g.user_set.count()) for g in Group.objects.all()])
print('Sample users:', [(u.username, u.is_staff, list(u.groups.values_list('name', flat=True))) for u in User.objects.all()[:5]])
"

# Check application logs for errors
tail -f /var/log/lcstats/error.log  # Adjust path to your log file

# Test key URLs manually:
# - /homework/teacher/ (should work for teachers only)
# - /homework/ (should work for students and teachers)
# - Create a test student account and verify group assignment
```

## Rollback Procedure

If something goes wrong, you can safely rollback:

```bash
# SSH into production server
ssh your-server
cd /path/to/lcstats
source venv/bin/activate

# Rollback the migration
python manage.py migrate students 0007

# Restart application
sudo systemctl restart lcstats  # or your restart command

# Restore database from backup (if needed)
mysql -u morgan -p lcaim < backup_before_groups_YYYYMMDD_HHMMSS.sql
```

## What the Migration Does

1. **Creates two groups**: Students and Teachers
2. **Assigns existing users**:
   - Users with `is_staff=True` → Teachers group
   - Users with `is_staff=False` → Students group
3. **Enables automatic assignment**: New users are auto-assigned to groups based on their registration code type

## Testing After Deployment

### Test 1: Teacher Access
```bash
# Login as a teacher account
# Navigate to /homework/teacher/
# Should see teacher dashboard
```

### Test 2: Student Access
```bash
# Login as a student account
# Navigate to /homework/teacher/
# Should see "Permission Denied" error
```

### Test 3: New User Registration
```bash
# Create a new student with a student registration code
# Verify in admin that they're in Students group

# Create a new teacher with a teacher registration code
# Verify in admin that they're in Teachers group
```

### Test 4: Check Logs
```bash
# Check for any permission-related errors
grep -i "permission" /var/log/lcstats/error.log
grep -i "group" /var/log/lcstats/error.log
```

## Monitoring After Deployment

- Monitor for 24-48 hours after deployment
- Check error logs daily
- Verify no users reporting access issues
- Confirm new user registrations are working

## Support Information

**Migration can be rolled back safely** - No data is deleted, only group assignments are added/removed.

**If users report permission issues**:
1. Check their group membership in Django Admin
2. Verify they have a StudentProfile (created automatically on user creation)
3. For teachers, verify they have a TeacherProfile
4. Check error logs for PermissionDenied exceptions

**Emergency contacts**:
- Review this deployment doc: `DEPLOYMENT_GROUPS.md`
- Check migration file: `students/migrations/0008_setup_user_groups.py`
- Review decorator code: `students/decorators.py`

## Success Criteria

✅ Migration completes without errors
✅ All existing users assigned to groups
✅ Teachers can access teacher-only views
✅ Students cannot access teacher-only views
✅ New user registration assigns correct groups
✅ No permission errors in logs
✅ All homework functionality works as before

## Notes

- This change is **backward compatible** - existing functionality continues to work
- The `is_staff` flag is still maintained for Django admin access
- Groups provide additional permission granularity for future features
- No changes to database schema (only data in auth_group and auth_user_groups tables)