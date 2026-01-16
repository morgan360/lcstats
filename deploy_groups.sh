#!/bin/bash
# Quick deployment script for Django Groups migration
# Run this on your production server after pulling the latest code

set -e  # Exit on error

echo "=== Django Groups Migration Deployment ==="
echo "Starting deployment at $(date)"
echo ""

# Check if we're in the right directory
if [ ! -f "manage.py" ]; then
    echo "Error: manage.py not found. Please run this from the project root."
    exit 1
fi

# Activate virtual environment
echo "1. Activating virtual environment..."
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d "env" ]; then
    source env/bin/activate
else
    echo "Warning: Virtual environment not found. Proceeding anyway..."
fi

# Show current migration status
echo ""
echo "2. Current migration status:"
python manage.py showmigrations students | tail -5

# Run the migration
echo ""
echo "3. Running migration..."
python manage.py migrate students

# Verify groups were created
echo ""
echo "4. Verifying groups:"
python manage.py shell -c "
from django.contrib.auth.models import Group, User
groups = Group.objects.all()
print(f'✓ Groups created: {groups.count()}')
for group in groups:
    print(f'  - {group.name}: {group.user_set.count()} users')

# Check sample users
print('\n✓ Sample user assignments:')
for user in User.objects.all()[:3]:
    groups_list = ', '.join([g.name for g in user.groups.all()])
    print(f'  - {user.username} (staff={user.is_staff}): {groups_list}')
"

echo ""
echo "5. Collecting static files..."
python manage.py collectstatic --noinput --clear

echo ""
echo "=== Deployment Complete ==="
echo "Finished at $(date)"
echo ""
echo "Next steps:"
echo "1. Restart your application server (systemctl/supervisor/apache)"
echo "2. Test teacher and student logins"
echo "3. Monitor logs for any permission errors"
echo ""
echo "To rollback if needed:"
echo "  python manage.py migrate students 0007"