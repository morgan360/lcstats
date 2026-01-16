#!/usr/bin/env python
"""
Fix Tanzer's group membership - add to both Students and Teachers groups
Run this on PythonAnywhere after migration
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lcstats.settings')
django.setup()

from django.contrib.auth.models import User, Group

# Find Tanzer
try:
    tanzer = User.objects.get(username='Tanzer')
    print(f"Found user: {tanzer.username}")
    print(f"  is_staff: {tanzer.is_staff}")
    print(f"  is_superuser: {tanzer.is_superuser}")
    print(f"  Current groups: {[g.name for g in tanzer.groups.all()]}")

    # Get both groups
    students_group = Group.objects.get(name='Students')
    teachers_group = Group.objects.get(name='Teachers')

    # Add to both groups
    tanzer.groups.add(students_group)
    tanzer.groups.add(teachers_group)

    print(f"\n✓ Added Tanzer to both groups")
    print(f"  New groups: {[g.name for g in tanzer.groups.all()]}")
    print(f"\nTanzer should now appear in:")
    print(f"  - Student class lists (Students group)")
    print(f"  - Teacher dashboard (Teachers group)")
    print(f"  - Django admin (is_staff=True)")

except User.DoesNotExist:
    print("User 'Tanzer' not found. Please check the username.")
except Group.DoesNotExist as e:
    print(f"Group not found: {e}")
    print("Make sure the migration has been run: python manage.py migrate students")