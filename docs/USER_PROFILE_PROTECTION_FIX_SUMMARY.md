# User Profile Protection Fix - Complete Summary

## Problem Identified

You found that changing a teacher's username (RB_Teacher → AMcDonnell) broke the system. The same issue exists for **all** user profile relationships.

**Root Cause:** Using `on_delete=models.CASCADE` on OneToOneField relationships between User and Profile models means:
- Deleting/changing a User **should** cascade delete the Profile
- But when it fails (or username is changed), it creates **orphaned** Profile records
- These orphaned profiles still reference non-existent users
- Django admin breaks, showing old usernames that don't exist

## Solution: Changed CASCADE to PROTECT

Changed the `on_delete` behavior for user profile relationships from `CASCADE` to `PROTECT`.

### What PROTECT Means:

✅ **You CAN safely:**
- Change usernames (RB_Teacher → AMcDonnell)
- Change emails, names, passwords, etc.
- All relationships stay intact

✅ **Database PROTECTS you from:**
- Accidentally deleting a User that has a dependent Profile
- Creating orphaned records
- Breaking relationships

❌ **You CANNOT:**
- Delete a User if a Profile depends on it
- Django will show error: "Cannot delete User because Profile depends on it"

## Changes Made

### 1. TeacherProfile (`homework/models.py`)

**Line 19:** Changed from CASCADE to PROTECT
**Lines 43-53:** Added defensive `__str__` method

```python
# Before
user = models.OneToOneField(User, on_delete=models.CASCADE)

# After
user = models.OneToOneField(User, on_delete=models.PROTECT)

def __str__(self):
    if self.display_name:
        return self.display_name
    try:
        return self.user.get_full_name() or self.user.username
    except User.DoesNotExist:
        return f"TeacherProfile #{self.pk} (orphaned)"
```

**Migration:** `homework/migrations/0007_change_teacherprofile_to_protect.py` ✅ Applied

### 2. StudentProfile (`students/models.py`)

**Lines 15-18:** Changed from CASCADE to PROTECT
**Lines 32-39:** Added defensive `__str__` method

```python
# Before
user = models.OneToOneField(User, on_delete=models.CASCADE)

# After
user = models.OneToOneField(
    User,
    on_delete=models.PROTECT,
    help_text="User account for this student"
)

def __str__(self):
    try:
        return self.user.username
    except User.DoesNotExist:
        return f"StudentProfile #{self.pk} (orphaned)"
```

**Migration:** `students/migrations/0011_change_studentprofile_to_protect.py` ✅ Applied

## Other CASCADE Relationships Checked

These CASCADE relationships are **correct** and should stay as-is:

### Students App:
- ✅ `QuestionAttempt.student → StudentProfile` (CASCADE is correct - delete attempts when profile deleted)
- ✅ `QuestionAttempt.question → Question` (CASCADE is correct - delete attempts when question deleted)
- ✅ `LoginHistory.user → User` (CASCADE is correct - delete login history when user deleted)
- ✅ `UserSession.user → User` (CASCADE is correct - delete sessions when user deleted)

### Homework App:
- ✅ `TeacherClass.teacher → TeacherProfile` (CASCADE is correct - delete classes when teacher profile deleted)
- ✅ `HomeworkAssignment.teacher → TeacherProfile` (CASCADE is correct - delete assignments when teacher profile deleted)
- ✅ `HomeworkTask.assignment → HomeworkAssignment` (CASCADE is correct - delete tasks when assignment deleted)
- ✅ `StudentHomeworkProgress.student → User` (CASCADE is correct - delete progress when user deleted)

### Registration Codes:
- ✅ `RegistrationCode.teacher_class → TeacherClass` (SET_NULL is correct - keep code if class deleted)
- ✅ `RegistrationCode.created_by → User` (SET_NULL is correct - keep code if creator deleted)

## Impact & Benefits

### Before (CASCADE):
| Action | Result | Problem |
|--------|--------|---------|
| Change username | Should cascade delete profile | ❌ Sometimes failed, creating orphans |
| Delete user | Profile deleted automatically | ❌ Accident-prone |
| Orphaned profiles | Possible | ❌ Breaks admin interface |

### After (PROTECT):
| Action | Result | Benefit |
|--------|--------|---------|
| Change username | ✅ Works perfectly | Safe to change usernames anytime |
| Delete user | ❌ Blocked by database | Prevents accidental data loss |
| Orphaned profiles | ✅ Prevented by constraint | No more broken references |

## How to Use Going Forward

### Changing a Username:
1. Go to `/admin/auth/user/`
2. Find the user
3. Change `username` field
4. Save
5. ✅ **Everything stays connected!**

### Changing Display Names:
**For Teachers:**
1. Go to `/admin/homework/teacherprofile/`
2. Change `display_name` field
3. Save

**For Students:**
- Students don't have a display_name field
- Just change the User's first_name/last_name

### Proper Deletion Process:
**To delete a teacher:**
1. Delete TeacherProfile first (cascades to classes/assignments)
2. Then delete the User

**To delete a student:**
1. Delete StudentProfile first (cascades to attempts/progress)
2. Then delete the User

**Or use Django admin cascade:**
- When you try to delete a User, Django will show what will be deleted
- Review and confirm if you want to proceed

## Fixing Orphaned Records (Production)

If you have orphaned profiles on your live site, run this in Django shell:

```python
from homework.models import TeacherProfile
from students.models import StudentProfile
from django.contrib.auth.models import User

# Check and fix TeacherProfiles
print("Checking TeacherProfiles...")
for tp in TeacherProfile.objects.all():
    try:
        _ = tp.user.username
        print(f"  ✓ {tp}")
    except User.DoesNotExist:
        print(f"  ❌ Orphaned: TeacherProfile #{tp.pk}")
        # Option 1: Delete it
        # tp.delete()

        # Option 2: Fix it (if you know the new username)
        # new_user = User.objects.get(username='AMcDonnell')
        # tp.user = new_user
        # tp.save()

# Check and fix StudentProfiles
print("\nChecking StudentProfiles...")
for sp in StudentProfile.objects.all():
    try:
        _ = sp.user.username
        print(f"  ✓ {sp}")
    except User.DoesNotExist:
        print(f"  ❌ Orphaned: StudentProfile #{sp.pk}")
        # Decide whether to delete or fix
```

## Database Integrity Check Script

Add this management command to periodically check for orphaned records:

```python
# students/management/commands/check_profile_integrity.py
from django.core.management.base import BaseCommand
from homework.models import TeacherProfile
from students.models import StudentProfile
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Check for orphaned user profiles'

    def handle(self, *args, **options):
        orphaned_teachers = []
        orphaned_students = []

        # Check TeacherProfiles
        for tp in TeacherProfile.objects.all():
            try:
                _ = tp.user.username
            except User.DoesNotExist:
                orphaned_teachers.append(tp)

        # Check StudentProfiles
        for sp in StudentProfile.objects.all():
            try:
                _ = sp.user.username
            except User.DoesNotExist:
                orphaned_students.append(sp)

        # Report
        if orphaned_teachers:
            self.stdout.write(
                self.style.WARNING(
                    f'⚠️  Found {len(orphaned_teachers)} orphaned TeacherProfiles'
                )
            )
            for tp in orphaned_teachers:
                self.stdout.write(f'  - TeacherProfile #{tp.pk}')

        if orphaned_students:
            self.stdout.write(
                self.style.WARNING(
                    f'⚠️  Found {len(orphaned_students)} orphaned StudentProfiles'
                )
            )
            for sp in orphaned_students:
                self.stdout.write(f'  - StudentProfile #{sp.pk}')

        if not orphaned_teachers and not orphaned_students:
            self.stdout.write(
                self.style.SUCCESS('✅ All profiles have valid users')
            )
```

## Deployment to Production

```bash
# On production server
cd ~/lcstats
source venv/bin/activate
git pull origin main

# Apply migrations
python manage.py migrate homework
python manage.py migrate students

# Optional: Check for orphaned profiles
python manage.py check_profile_integrity

# Reload WSGI app
touch /var/www/your_wsgi_file.py
```

## Summary

✅ **Fixed:** TeacherProfile.user relationship
✅ **Fixed:** StudentProfile.user relationship
✅ **Migration created and applied:** Both apps migrated successfully
✅ **Defensive __str__ methods:** Handle edge cases gracefully
✅ **Verified:** All other CASCADE relationships are appropriate

**Result:** You can now safely change usernames without breaking the system!

---

**Status:** ✅ Completed and tested locally
**Next:** Deploy to production and fix any orphaned profiles
**Files Modified:**
- `homework/models.py`
- `students/models.py`
- Created 2 migrations