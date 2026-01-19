# Teacher User Protection Fix - Database Relationship Improvement

## Problem

When you changed a teacher's username from `RB_Teacher` to `AMcDonnell`, the system broke because:

1. `TeacherProfile.user` had `on_delete=models.CASCADE`
2. Deleting or changing the user should have cascaded to delete the `TeacherProfile`
3. But it didn't work properly, creating an "orphaned" `TeacherProfile`
4. The `TeacherClass` still pointed to this orphaned profile
5. Django admin showed "RB_Teacher" even though the user didn't exist

**Root cause:** Changing a username shouldn't break the entire teacher/class/homework system!

## Solution Implemented

Changed `TeacherProfile.user` relationship from `CASCADE` to `PROTECT`:

### Before:
```python
user = models.OneToOneField(
    User,
    on_delete=models.CASCADE,  # ❌ Deletes TeacherProfile if User is deleted
    ...
)
```

### After:
```python
user = models.OneToOneField(
    User,
    on_delete=models.PROTECT,  # ✅ Prevents User deletion if TeacherProfile exists
    ...
)
```

## What This Means

### Now:
- ✅ **You CAN** change a teacher's username safely (just updates User.username)
- ✅ **You CAN** change a teacher's email, full name, etc.
- ✅ **You CANNOT** accidentally delete a User if a TeacherProfile depends on it
- ✅ **Defensive __str__** method shows "(orphaned)" if user somehow doesn't exist

### Behavior:
1. **Changing username:** Works fine - just updates the User object
2. **Deleting user:** Django will **block** it and show an error: "Cannot delete User because TeacherProfile depends on it"
3. **Proper deletion process:**
   - First delete TeacherProfile (which cascades to TeacherClass and HomeworkAssignment)
   - Then you can delete the User

## Changes Made

### 1. Model Change (`homework/models.py`)

**Line 19:** Changed `on_delete=models.CASCADE` to `on_delete=models.PROTECT`

**Lines 43-53:** Improved `__str__` method with defensive programming:
```python
def __str__(self):
    """
    Return display name, falling back to user's name/username.
    Handles case where user might not exist (defensive programming).
    """
    if self.display_name:
        return self.display_name
    try:
        return self.user.get_full_name() or self.user.username
    except User.DoesNotExist:
        return f"TeacherProfile #{self.pk} (orphaned)"
```

### 2. Migration Created

**File:** `homework/migrations/0007_change_teacherprofile_to_protect.py`

**Applied:** Yes - migration ran successfully

## Fixing Your Current Issue

You still need to fix the orphaned TeacherProfile on your live site. Here's the Django shell command:

```python
from homework.models import TeacherProfile
from django.contrib.auth.models import User

# Find orphaned profiles
for tp in TeacherProfile.objects.all():
    try:
        _ = tp.user.username
        print(f"✓ {tp.display_name or tp.user.username} - OK")
    except User.DoesNotExist:
        print(f"❌ TeacherProfile #{tp.pk} is orphaned")

        # FIX: Point it to AMcDonnell
        new_user = User.objects.get(username='AMcDonnell')
        tp.user = new_user
        tp.display_name = "A. McDonnell"  # Optional but recommended
        tp.save()
        print(f"✅ Fixed - now points to {new_user.username}")
```

## Comparison: CASCADE vs PROTECT

| Scenario | CASCADE (Old) | PROTECT (New) |
|----------|---------------|---------------|
| Delete User | TeacherProfile deleted automatically | ❌ **Blocked** - must delete TeacherProfile first |
| Change username | Should work (didn't always) | ✅ **Works perfectly** |
| Orphaned records | Possible if CASCADE fails | ✅ **Prevented** by database constraint |
| Safety | Low - easy to accidentally delete | ✅ **High** - explicit deletion required |

## Best Practices Going Forward

### To Change a Teacher's Username:
1. Go to `/admin/auth/user/`
2. Find the user
3. Change `username` field
4. Click Save
5. ✅ **Done!** Everything else stays connected

### To Change a Teacher's Display Name:
1. Go to `/admin/homework/teacherprofile/`
2. Find the teacher profile
3. Change `display_name` field
4. Click Save
5. ✅ This shows in admin instead of username

### To Properly Delete a Teacher:
1. Go to `/admin/homework/teacherprofile/`
2. Delete the TeacherProfile first (cascades to classes and assignments)
3. Then go to `/admin/auth/user/`
4. Delete the User

## Database Integrity Check (Optional)

Add this to a management command to find orphaned records:

```python
from homework.models import TeacherProfile
from django.contrib.auth.models import User

def check_teacher_integrity():
    """Check for orphaned teacher profiles."""
    orphaned = []
    for tp in TeacherProfile.objects.all():
        try:
            _ = tp.user.username
        except User.DoesNotExist:
            orphaned.append(tp)

    if orphaned:
        print(f"⚠️ Found {len(orphaned)} orphaned TeacherProfiles:")
        for tp in orphaned:
            print(f"  - ID: {tp.pk}")
    else:
        print("✅ All TeacherProfiles have valid users")

    return orphaned
```

## Deployment to Production

```bash
# On production server
cd ~/lcstats
source venv/bin/activate
git pull origin main
python manage.py migrate homework
# Reload app (touch wsgi or restart)
```

## Summary

**Before:** Fragile - changing username could break everything
**After:** Robust - changing username just works, with database protection against accidental deletions

---

**Status:** ✅ Completed and migrated locally
**Next:** Deploy to production and fix the orphaned profile