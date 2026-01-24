#!/usr/bin/env python3
"""
Diagnostic script to verify follow-up email templates are deployed correctly.
Run this on PythonAnywhere console to check if deployment worked.
"""

import os
from pathlib import Path

print("=" * 70)
print("🔍 DEPLOYMENT VERIFICATION SCRIPT")
print("=" * 70)

# Check if we're in the right directory
current_dir = Path.cwd()
print(f"\n📁 Current directory: {current_dir}")

# Check for lcstats directory
if not (current_dir.name == 'lcstats' or (current_dir / 'manage.py').exists()):
    print("⚠️  WARNING: Not in lcstats directory!")
    print("   Run: cd ~/lcstats")
else:
    print("✅ In correct directory")

# Check Git status
print("\n📊 Git Status:")
print("-" * 70)
os.system("git log --oneline -3")

# Check if templates exist
print("\n📧 Email Templates:")
print("-" * 70)
template_dir = Path("schools/templates/schools/emails")

if template_dir.exists():
    print(f"✅ Template directory exists: {template_dir}")

    templates = {
        "initial_outreach.html": False,
        "initial_outreach.txt": False,
        "follow_up.html": False,
        "follow_up.txt": False,
    }

    for template_file in templates.keys():
        file_path = template_dir / template_file
        if file_path.exists():
            templates[template_file] = True
            size = file_path.stat().st_size
            print(f"  ✅ {template_file} ({size} bytes)")
        else:
            templates[template_file] = False
            print(f"  ❌ {template_file} MISSING!")

    # Check if follow-up templates exist
    if templates["follow_up.html"] and templates["follow_up.txt"]:
        print("\n✅ Follow-up templates are deployed!")
    else:
        print("\n❌ Follow-up templates are MISSING - need to git pull")

else:
    print(f"❌ Template directory doesn't exist: {template_dir}")

# Check admin.py for follow-up support
print("\n🔧 Admin Code Check:")
print("-" * 70)
admin_file = Path("schools/admin.py")

if admin_file.exists():
    with open(admin_file, 'r') as f:
        admin_content = f.read()

    if "if email_type == 'follow_up':" in admin_content:
        print("✅ admin.py has follow-up template support")
    else:
        print("❌ admin.py MISSING follow-up template logic - need to git pull")
else:
    print("❌ admin.py not found!")

# Check if web app needs reload
print("\n🔄 Next Steps:")
print("-" * 70)
print("1. If templates are missing: Run 'git pull origin main'")
print("2. Go to PythonAnywhere Web tab")
print("3. Click the green 'Reload' button for numscoil.ie")
print("4. Wait 10 seconds for reload to complete")
print("5. Try sending test email again")

print("\n" + "=" * 70)
print("✅ Diagnostic complete!")
print("=" * 70)