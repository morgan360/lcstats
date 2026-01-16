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
    - Manage exam papers (exam_papers app)
    - Manage homework assignments (homework app)
    - Manage classes and students
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
        # Exam Papers app
        ('exam_papers', 'ExamPaper'),
        ('exam_papers', 'ExamQuestion'),
        ('exam_papers', 'ExamQuestionPart'),

        # Homework app
        ('homework', 'HomeworkAssignment'),
        ('homework', 'HomeworkTask'),
        ('homework', 'TeacherClass'),
        ('homework', 'TeacherProfile'),

        # Students (for managing class enrollment)
        ('students', 'StudentProfile'),

        # Auth (to see users for class enrollment)
        ('auth', 'User'),  # View only added below
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
    print("    - Exam papers and questions")
    print("    - Homework assignments and tasks")
    print("    - Classes and teacher profiles")

    return teacher_admin_group


def add_user_to_teacher_admin(username):
    """Add a specific user to Teacher Admins group and give them is_staff"""
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

        # Add to Students group (so they appear in class lists)
        students_group, _ = Group.objects.get_or_create(name='Students')
        user.groups.add(students_group)

        user.save()

        print(f"\n✓ {username} configured:")
        print(f"  - is_staff: {user.is_staff}")
        print(f"  - is_superuser: {user.is_superuser}")
        print(f"  - Groups: {', '.join([g.name for g in user.groups.all()])}")
        print(f"\n{username} can now:")
        print(f"  ✓ Access Django Admin (limited permissions)")
        print(f"  ✓ Upload and edit exam papers")
        print(f"  ✓ Create and manage homework")
        print(f"  ✓ Manage classes")
        print(f"  ✓ Access Teacher Dashboard")
        print(f"  ✓ Appear in student class lists")

    except User.DoesNotExist:
        print(f"✗ User '{username}' not found")


if __name__ == '__main__':
    print("=" * 60)
    print("Setting up Teacher Admin Permissions")
    print("=" * 60)

    # Create the Teacher Admins group with permissions
    setup_teacher_admin_group()

    # Add Tanzer to Teacher Admins
    print("\n" + "=" * 60)
    print("Adding Tanzer to Teacher Admins")
    print("=" * 60)
    add_user_to_teacher_admin('Tanzer')

    print("\n" + "=" * 60)
    print("Setup Complete!")
    print("=" * 60)
