#!/usr/bin/env python
"""
Add specific staff/superusers to Students group so they appear in class lists
Useful for admin accounts that also need to be students
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lcstats.settings')
django.setup()

from django.contrib.auth.models import User, Group

# List of usernames that should be in BOTH Teachers and Students groups
DUAL_ROLE_USERS = [
    'Tanzer',  # Add more usernames here if needed
]

def add_to_both_groups():
    students_group = Group.objects.get(name='Students')
    teachers_group = Group.objects.get(name='Teachers')

    print("Adding users to both Students and Teachers groups:")
    print("=" * 60)

    for username in DUAL_ROLE_USERS:
        try:
            user = User.objects.get(username=username)

            # Add to both groups
            user.groups.add(students_group)
            user.groups.add(teachers_group)

            print(f"\n✓ {username}")
            print(f"  Groups: {', '.join([g.name for g in user.groups.all()])}")
            print(f"  Staff: {user.is_staff}, Superuser: {user.is_superuser}")

        except User.DoesNotExist:
            print(f"\n✗ User '{username}' not found - skipping")

    print("\n" + "=" * 60)
    print("Done! Users should now appear in class student lists.")

if __name__ == '__main__':
    try:
        add_to_both_groups()
    except Group.DoesNotExist as e:
        print(f"Error: {e}")
        print("Make sure migration has been run: python manage.py migrate students")