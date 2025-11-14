# Migration Fix for UserSession Error

## Problem
You're seeing this error:
```
(1054, "Unknown column 'students_usersession.session_key' in 'field list'")
```

This occurred because the database schema doesn't match the current Django models.

## Solution

Run the following command in your terminal (make sure you're in the project directory with your virtual environment activated):

```bash
python manage.py migrate students
```

This will apply migration `0006_fix_usersession_schema.py`, which will:
1. Drop the old `LoginHistory` and `UserSession` tables
2. Recreate them with the correct schema including the `session_key` field

**Note:** This will clear any existing session tracking and login history data, but this is acceptable as it's non-critical data.

## Steps to Run

1. Activate your virtual environment:
   ```bash
   source .venv/bin/activate  # On macOS/Linux
   # or
   .venv\Scripts\activate  # On Windows
   ```

2. Run the migration:
   ```bash
   python manage.py migrate
   ```

3. Restart your Django development server

The error should now be resolved.
