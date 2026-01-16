#!/usr/bin/env python
"""
Test script to verify Django Groups setup before deployment.
Run this locally before pushing to production.

Usage: python test_groups.py
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lcstats.settings')
django.setup()

from django.contrib.auth.models import User, Group
from students.models import RegistrationCode, StudentProfile
from homework.models import TeacherProfile

def test_groups_exist():
    """Test that groups were created"""
    print("\n=== Test 1: Groups Exist ===")
    students_group = Group.objects.filter(name='Students').first()
    teachers_group = Group.objects.filter(name='Teachers').first()

    assert students_group is not None, "Students group not found!"
    assert teachers_group is not None, "Teachers group not found!"

    print(f"✓ Students group exists ({students_group.user_set.count()} users)")
    print(f"✓ Teachers group exists ({teachers_group.user_set.count()} users)")

def test_existing_users_assigned():
    """Test that existing users were assigned to groups"""
    print("\n=== Test 2: Existing Users Assigned ===")

    for user in User.objects.all()[:5]:
        groups = list(user.groups.values_list('name', flat=True))
        assert len(groups) > 0, f"User {user.username} has no groups!"

        # Teachers should be in Teachers group
        if user.is_staff:
            assert 'Teachers' in groups, f"Teacher {user.username} not in Teachers group!"
            print(f"✓ {user.username} (teacher) → {', '.join(groups)}")
        else:
            assert 'Students' in groups, f"Student {user.username} not in Students group!"
            print(f"✓ {user.username} (student) → {', '.join(groups)}")

def test_new_user_auto_assigned():
    """Test that new users get auto-assigned to groups"""
    print("\n=== Test 3: New User Auto-Assignment ===")

    # Create a test student user
    test_username = f'test_student_{User.objects.count()}'
    test_user = User.objects.create_user(
        username=test_username,
        password='testpass123'
    )

    # Check if auto-assigned to Students group
    groups = list(test_user.groups.values_list('name', flat=True))
    assert 'Students' in groups, f"New user {test_username} not auto-assigned to Students group!"
    print(f"✓ New user {test_username} auto-assigned to Students group")

    # Check if StudentProfile was created
    assert hasattr(test_user, 'studentprofile'), "StudentProfile not created!"
    print(f"✓ StudentProfile created automatically")

    # Cleanup
    test_user.delete()
    print(f"✓ Test user cleaned up")

def test_decorators_importable():
    """Test that decorators can be imported"""
    print("\n=== Test 4: Decorators Importable ===")

    try:
        from students.decorators import (
            teacher_required,
            student_required,
            student_or_teacher_required,
            group_required
        )
        print("✓ All decorators imported successfully")
    except ImportError as e:
        raise AssertionError(f"Failed to import decorators: {e}")

def test_migration_reversible():
    """Test that migration can be reversed"""
    print("\n=== Test 5: Migration Reversibility ===")

    from django.db import connection
    from django.db.migrations.executor import MigrationExecutor

    executor = MigrationExecutor(connection)

    # Check current state
    current_state = executor.loader.project_state(('students', '0008_setup_user_groups'))
    print("✓ Migration 0008 is applied")

    # Check rollback is available
    plan = executor.migration_plan([('students', '0007_add_registration_code_types')])
    assert len(plan) > 0, "Rollback plan not available!"
    print("✓ Rollback to 0007 is available")

def main():
    """Run all tests"""
    print("=" * 60)
    print("Django Groups - Pre-Deployment Tests")
    print("=" * 60)

    try:
        test_groups_exist()
        test_existing_users_assigned()
        test_new_user_auto_assigned()
        test_decorators_importable()
        test_migration_reversible()

        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED - Safe to deploy!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. git add students/migrations/0008_setup_user_groups.py")
        print("2. git add students/decorators.py")
        print("3. git add students/signals.py")
        print("4. git add homework/views.py")
        print("5. git commit -m 'Add Django Groups for permissions'")
        print("6. git push origin main")
        print("7. Deploy to production (see DEPLOYMENT_GROUPS.md)")

        return 0

    except AssertionError as e:
        print("\n" + "=" * 60)
        print(f"❌ TEST FAILED: {e}")
        print("=" * 60)
        return 1
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"❌ ERROR: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    exit(main())