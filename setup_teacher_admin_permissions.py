#!/usr/bin/env python
"""
Set up limited admin permissions for teachers who need to:
- Upload and edit exam papers
- Create and manage homework assignments
- Manage their classes

This gives them Django Admin access to specific models only,
not full superuser access.
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lcstats.settings')
django.setup()

from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType

def setup_teacher_admin_group():
    """
    Create a 'Teacher Admins' group with permissions to:
    - Manage homework assignments (homework app)
    - Manage classes and students (their school only)

    Teachers do NOT have access to:
    - User accounts (superuser only)
    - Exam papers (superuser/exam admin only)
    """

    # Create the group
    teacher_admin_group, created = Group.objects.get_or_create(name='Teacher Admins')

    if created:
        print("✓ Created 'Teacher Admins' group")
    else:
        print("✓ 'Teacher Admins' group already exists")

    # Clear existing permissions
    teacher_admin_group.permissions.clear()

    # Define models that Teacher Admins can manage
    app_model_permissions = [
        # Homework app - core teacher functionality
        ('homework', 'HomeworkAssignment'),
        ('homework', 'HomeworkTask'),
        ('homework', 'TeacherClass'),
        ('homework', 'TeacherProfile'),

        # Students (for managing class enrollment and viewing progress)
        ('students', 'StudentProfile'),

        # NOTE: Teachers do NOT have access to:
        # - auth.User (only superusers manage user accounts)
        # - exam_papers (only superusers/exam admins upload exam papers)
        # - Groups, Permissions (admin-only)
    ]

    permissions_added = []

    for app_label, model_name in app_model_permissions:
        try:
            content_type = ContentType.objects.get(app_label=app_label, model=model_name.lower())

            # Add add, change, delete, view permissions
            for perm_type in ['add', 'change', 'delete', 'view']:
                codename = f'{perm_type}_{model_name.lower()}'
                try:
                    permission = Permission.objects.get(
                        codename=codename,
                        content_type=content_type
                    )
                    teacher_admin_group.permissions.add(permission)
                    permissions_added.append(f"{perm_type} {model_name}")
                except Permission.DoesNotExist:
                    print(f"  ⚠ Permission not found: {codename}")

        except ContentType.DoesNotExist:
            print(f"  ⚠ Model not found: {app_label}.{model_name}")

    print(f"\n✓ Added {len(permissions_added)} permissions to Teacher Admins group")
    print("  Permissions include: add, change, delete, view for:")
    print("    - Homework assignments and tasks")
    print("    - Classes and teacher profiles")
    print("    - Student profiles (filtered by school)")

    return teacher_admin_group


def setup_exam_admin_group():
    """
    Create 'Exam Admins' group for users like Tanzer who only manage exam papers.
    """
    exam_admin_group, created = Group.objects.get_or_create(name='Exam Admins')

    if created:
        print("✓ Created 'Exam Admins' group")
    else:
        print("✓ 'Exam Admins' group already exists")

    # Clear existing permissions
    exam_admin_group.permissions.clear()

    # Only exam papers permissions
    app_model_permissions = [
        ('exam_papers', 'ExamPaper'),
        ('exam_papers', 'ExamQuestion'),
        ('exam_papers', 'ExamQuestionPart'),
    ]

    permissions_added = []

    for app_label, model_name in app_model_permissions:
        try:
            content_type = ContentType.objects.get(app_label=app_label, model=model_name.lower())

            for perm_type in ['add', 'change', 'delete', 'view']:
                codename = f'{perm_type}_{model_name.lower()}'
                try:
                    permission = Permission.objects.get(
                        codename=codename,
                        content_type=content_type
                    )
                    exam_admin_group.permissions.add(permission)
                    permissions_added.append(f"{perm_type} {model_name}")
                except Permission.DoesNotExist:
                    print(f"  ⚠ Permission not found: {codename}")

        except ContentType.DoesNotExist:
            print(f"  ⚠ Model not found: {app_label}.{model_name}")

    print(f"✓ Added {len(permissions_added)} permissions to Exam Admins group")
    print("  Permissions: add, change, delete, view exam papers only")

    return exam_admin_group


def add_exam_admin(username):
    """Add user to Exam Admins - can only manage exam papers"""
    try:
        user = User.objects.get(username=username)
        exam_admin_group = Group.objects.get(name='Exam Admins')

        # Give them is_staff (needed to access admin)
        user.is_staff = True

        # Add to Exam Admins group (for exam permissions only)
        user.groups.add(exam_admin_group)

        # Add to Students group (so they appear in class lists)
        students_group, _ = Group.objects.get_or_create(name='Students')
        user.groups.add(students_group)

        user.save()

        print(f"\n✓ {username} configured as Exam Admin:")
        print(f"  - is_staff: {user.is_staff}")
        print(f"  - is_superuser: {user.is_superuser}")
        print(f"  - Groups: {', '.join([g.name for g in user.groups.all()])}")
        print(f"\n{username} can now:")
        print(f"  ✓ Access Django Admin (exam papers only)")
        print(f"  ✓ Upload and edit exam papers")
        print(f"  ✓ Appear in student class lists")
        print(f"  ✗ Cannot manage homework (not a teacher)")

    except User.DoesNotExist:
        print(f"✗ User '{username}' not found")


def add_teacher_admin(username):
    """Add user to Teacher Admins - can manage homework and classes"""
    try:
        user = User.objects.get(username=username)
        teacher_admin_group = Group.objects.get(name='Teacher Admins')

        # Give them is_staff (needed to access admin)
        user.is_staff = True

        # Add to Teacher Admins group (for permissions)
        user.groups.add(teacher_admin_group)

        # Also ensure they're in Teachers group (for Teacher Dashboard)
        teachers_group, _ = Group.objects.get_or_create(name='Teachers')
        user.groups.add(teachers_group)

        # Add to Students group (so they appear in class lists if needed)
        students_group, _ = Group.objects.get_or_create(name='Students')
        user.groups.add(students_group)

        user.save()

        print(f"\n✓ {username} configured as Teacher Admin:")
        print(f"  - is_staff: {user.is_staff}")
        print(f"  - is_superuser: {user.is_superuser}")
        print(f"  - Groups: {', '.join([g.name for g in user.groups.all()])}")
        print(f"\n{username} can now:")
        print(f"  ✓ Access Django Admin (homework & classes only)")
        print(f"  ✓ Create and manage homework")
        print(f"  ✓ Manage classes and students (their school only)")
        print(f"  ✓ Access Teacher Dashboard")
        print(f"  ✗ Cannot upload exam papers (use superuser or exam admin)")

    except User.DoesNotExist:
        print(f"✗ User '{username}' not found")


if __name__ == '__main__':
    print("=" * 60)
    print("Setting up Admin Permissions")
    print("=" * 60)

    # Create both groups
    print("\n1. Creating Teacher Admins group (for teachers)...")
    setup_teacher_admin_group()

    print("\n2. Creating Exam Admins group (for exam managers)...")
    setup_exam_admin_group()

    # Add Tanzer as Exam Admin (can only manage exam papers + is a student)
    print("\n" + "=" * 60)
    print("Configuring Tanzer_Fernandes as Exam Admin")
    print("=" * 60)
    add_exam_admin('Tanzer_Fernandes')

    print("\n" + "=" * 60)
    print("Setup Complete!")
    print("=" * 60)
    print("\nTo add teachers with homework admin access, run:")
    print("  python manage.py shell")
    print("  >>> from setup_teacher_admin_permissions import add_teacher_admin")
    print("  >>> add_teacher_admin('teacher_username')")
    print("  >>> exit()")
