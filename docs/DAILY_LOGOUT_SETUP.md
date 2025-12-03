# Daily Automatic User Logout Setup

This document explains how to set up automatic daily logout of all users at 2am.

## Overview

The system logs out all users by clearing Django sessions at 2am every morning. This helps:
- Maintain security by ensuring stale sessions are cleared
- Force users to log in with fresh credentials regularly
- Clean up expired sessions from the database

## Components

### 1. Management Command

**File:** `students/management/commands/logout_all_users.py`

**Usage:**
```bash
# Log out all users immediately
python manage.py logout_all_users

# Dry run (see what would be deleted without actually deleting)
python manage.py logout_all_users --dry-run
```

**What it does:**
- Deletes all active sessions (logs out all users)
- Cleans up expired sessions
- Provides feedback on number of sessions deleted

### 2. Bash Script

**File:** `scripts/daily_logout.sh`

A wrapper script that:
- Activates the virtual environment
- Runs the logout command
- Logs the results with timestamps

## Setup Instructions

### For PythonAnywhere

1. **Test the command locally first:**
   ```bash
   python manage.py logout_all_users --dry-run
   ```

2. **Update the script with correct paths:**

   Edit `scripts/daily_logout.sh` and ensure paths match your PythonAnywhere setup:
   ```bash
   PROJECT_DIR="/home/morganvooght/lcstats"
   VENV_DIR="$PROJECT_DIR/.venv"
   ```

3. **Set up the scheduled task on PythonAnywhere:**

   a. Go to PythonAnywhere Dashboard → **Schedule** tab

   b. Click **"Create a new scheduled task"**

   c. Enter the time: **02:00** (for 2am)

   d. Enter the command:
   ```bash
   /home/morganvooght/lcstats/scripts/daily_logout.sh >> /home/morganvooght/logs/daily_logout.log 2>&1
   ```

   e. Click **"Create"**

4. **Create log directory:**
   ```bash
   mkdir -p ~/logs
   ```

5. **Test the script manually:**
   ```bash
   /home/morganvooght/lcstats/scripts/daily_logout.sh
   ```

6. **Check logs:**
   ```bash
   tail -f ~/logs/daily_logout.log
   ```

### Alternative: Using Cron (for other hosting)

If you're not using PythonAnywhere, you can use cron:

1. **Edit crontab:**
   ```bash
   crontab -e
   ```

2. **Add this line:**
   ```
   0 2 * * * /home/morganvooght/lcstats/scripts/daily_logout.sh >> /home/morganvooght/logs/daily_logout.log 2>&1
   ```

   This means:
   - `0 2 * * *` = Run at 2:00am every day
   - `>> /home/morganvooght/logs/daily_logout.log` = Append output to log file
   - `2>&1` = Redirect errors to the same log file

3. **Save and exit**

## Verification

### Check if it's working:

1. **Check the log file:**
   ```bash
   tail -20 ~/logs/daily_logout.log
   ```

   You should see entries like:
   ```
   Sun Dec  3 02:00:01 UTC 2025: Running daily user logout...
   Successfully logged out all users by deleting 5 session(s)
   Also cleaned up 3 expired session(s)
   Sun Dec  3 02:00:01 UTC 2025: Daily logout completed successfully
   ```

2. **Verify sessions are cleared:**
   ```bash
   python manage.py shell
   ```
   ```python
   from django.contrib.sessions.models import Session
   from django.utils import timezone

   # Check how many active sessions exist
   active = Session.objects.filter(expire_date__gte=timezone.now()).count()
   print(f"Active sessions: {active}")
   ```

3. **Test logout manually:**
   - Log in as a user before 2am
   - Check if you're logged out after 2am
   - Or run the command manually: `python manage.py logout_all_users`

## Troubleshooting

### Script doesn't run

**Check permissions:**
```bash
ls -l scripts/daily_logout.sh
# Should show: -rwxr-xr-x (executable)
```

**Make it executable if needed:**
```bash
chmod +x scripts/daily_logout.sh
```

### Virtual environment issues

**Check if venv path is correct:**
```bash
ls /home/morganvooght/lcstats/.venv/bin/activate
```

**Update the script if your venv is elsewhere:**
```bash
# Common alternatives:
VENV_DIR="$PROJECT_DIR/venv"
# or
VENV_DIR="$PROJECT_DIR/virtualenv"
```

### Sessions not being deleted

**Check database connection:**
```bash
python manage.py shell
```
```python
from django.contrib.sessions.models import Session
print(Session.objects.count())
```

**Check if Django sessions are configured:**

In `settings.py`, ensure you have:
```python
INSTALLED_APPS = [
    ...
    'django.contrib.sessions',
    ...
]

MIDDLEWARE = [
    ...
    'django.contrib.sessions.middleware.SessionMiddleware',
    ...
]
```

### Log file not created

**Create logs directory:**
```bash
mkdir -p ~/logs
touch ~/logs/daily_logout.log
```

**Check permissions:**
```bash
ls -ld ~/logs
# Should be writable
```

## Customization

### Change the logout time

Edit the cron schedule or PythonAnywhere task time:
- 2am: `0 2 * * *`
- 3am: `0 3 * * *`
- Midnight: `0 0 * * *`
- 1:30am: `30 1 * * *`

### Run multiple times per day

Add multiple cron entries:
```
0 2 * * * /path/to/daily_logout.sh >> /path/to/log 2>&1
0 14 * * * /path/to/daily_logout.sh >> /path/to/log 2>&1
```

### Exclude certain users (Advanced)

Modify `logout_all_users.py` to exclude specific users:

```python
from django.contrib.auth.models import User

# Get sessions for specific users only
exclude_usernames = ['admin', 'superuser']
exclude_user_ids = User.objects.filter(
    username__in=exclude_usernames
).values_list('id', flat=True)

# This would require custom session handling
# Django's default session model doesn't store user_id directly
```

**Note:** Django's default session model doesn't store user IDs directly, so excluding specific users requires custom implementation.

## Security Considerations

### Why log everyone out?

1. **Security:** Ensures old sessions can't be hijacked
2. **Updates:** Forces users to get fresh session with any new permissions
3. **Cleanup:** Removes orphaned sessions from database

### When NOT to use this

- If users need persistent sessions (e.g., "Remember Me" functionality)
- If you have users in different timezones who might be active at 2am UTC
- If your application requires 24/7 uninterrupted access

### Better alternatives

Consider these instead if daily logout is too aggressive:

1. **Session timeout:**
   In `settings.py`:
   ```python
   # Session expires after 2 weeks of inactivity
   SESSION_COOKIE_AGE = 1209600  # 14 days in seconds

   # Session expires when browser closes
   SESSION_EXPIRE_AT_BROWSER_CLOSE = True
   ```

2. **Regular cleanup without logout:**
   ```bash
   # Just clean expired sessions, don't delete active ones
   python manage.py clearsessions
   ```

3. **Gradual session expiry:**
   Let Django's built-in session expiration handle it naturally

## Monitoring

### Set up email notifications

Modify `scripts/daily_logout.sh` to send email on failure:

```bash
#!/bin/bash
# ... existing code ...

# Run the logout command
python manage.py logout_all_users

# Check result and email on failure
if [ $? -ne 0 ]; then
    echo "Daily logout failed!" | mail -s "LCAI Maths: Daily logout failed" your@email.com
fi
```

### Track in application logs

Add logging to `logout_all_users.py`:

```python
import logging
logger = logging.getLogger(__name__)

def handle(self, *args, **options):
    # ... existing code ...
    logger.info(f'Daily logout: Deleted {session_count} active sessions')
```

## Support

If you encounter issues:
1. Check the log file: `~/logs/daily_logout.log`
2. Test the command manually: `python manage.py logout_all_users --dry-run`
3. Verify cron/schedule is running: Check PythonAnywhere dashboard or `crontab -l`
4. Check Django settings for session configuration