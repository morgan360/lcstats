# macOS-Specific Deployment Notes

## MySQL Backup on macOS

On macOS, MySQL uses a different socket location than Linux. Use these commands instead:

### Backup Database (macOS)
```bash
# Option 1: Using socket path
mysqldump --socket=/tmp/mysql.sock -u morgan -p lcaim > backup_before_groups_$(date +%Y%m%d_%H%M%S).sql

# Option 2: Using TCP/IP (recommended)
mysqldump -h 127.0.0.1 -u morgan -p lcaim > backup_before_groups_$(date +%Y%m%d_%H%M%S).sql

# Option 3: Simple version (usually works)
mysqldump -u morgan -p -h 127.0.0.1 lcaim > backup_groups_$(date +%Y%m%d_%H%M%S).sql
```

### Restore Database (macOS)
```bash
# Option 1: Using socket path
mysql --socket=/tmp/mysql.sock -u morgan -p lcaim < backup_before_groups_YYYYMMDD_HHMMSS.sql

# Option 2: Using TCP/IP (recommended)
mysql -h 127.0.0.1 -u morgan -p lcaim < backup_before_groups_YYYYMMDD_HHMMSS.sql
```

## Quick Deploy on macOS (Development)

Since you're on macOS in development, you can skip the backup for local testing:

```bash
# 1. Commit changes
git add students/migrations/0008_setup_user_groups.py
git add students/decorators.py
git add students/signals.py
git add homework/views.py
git commit -m "Add Django Groups for student/teacher permissions"
git push origin main
```

**That's it for local!** The migration already ran successfully.

## Deploying to Production Server (Linux)

When you deploy to your production Linux server, use the original commands from `DEPLOYMENT_QUICKSTART.md`:

```bash
# SSH to production
ssh your-production-server

# Backup (Linux - original command works)
mysqldump -u morgan -p lcaim > backup_before_groups_$(date +%Y%m%d_%H%M%S).sql

# Deploy
cd /path/to/lcstats
git pull origin main
source venv/bin/activate
python manage.py migrate students
sudo systemctl restart lcstats
```

## Current Status

✅ Migration already applied locally (macOS)
✅ Groups created: Students (2), Teachers (1)
✅ All tests passed
✅ Ready to commit and push

## Next Steps

1. **Commit to Git:**
   ```bash
   git add .
   git commit -m "Add Django Groups for student/teacher permissions"
   git push origin main
   ```

2. **Deploy to Production** (when ready):
   - SSH to your production Linux server
   - Follow `DEPLOYMENT_QUICKSTART.md` or `DEPLOYMENT_GROUPS.md`
   - Use the Linux backup commands (they'll work there)

## Testing Locally (Optional)

You can test the permission system locally:

```bash
# Start dev server
python manage.py runserver

# Test teacher access: http://localhost:8000/homework/teacher/
# Test student access: http://localhost:8000/homework/
```

## Notes

- macOS MySQL uses `/tmp/mysql.sock` for socket connections
- Linux MySQL uses `/var/run/mysqld/mysqld.sock`
- Production deployment instructions assume Linux server
- Local (macOS) development already has migration applied