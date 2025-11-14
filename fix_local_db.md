# Fix Local Database Schema Issue

## Problem
Your local Mac database has an old schema for the `students_usersession` table (missing the `session_key` column), but production is working fine. This is a local-only issue.

## Solution Options

### Option 1: Re-apply Migration 0005 (Recommended)

This will fake-unapply migration 0005 and reapply it with the correct schema:

```bash
# Activate your virtual environment first
source .venv/bin/activate

# Fake-unapply migration 0005
python manage.py migrate students 0004 --fake

# Drop the old tables manually via MySQL
mysql -u morgan -p lcaim -e "DROP TABLE IF EXISTS students_usersession; DROP TABLE IF EXISTS students_loginhistory;"

# Re-apply migration 0005 (this time with correct schema)
python manage.py migrate students 0005
```

### Option 2: Manual SQL Fix (Faster)

If you want to keep your existing data in LoginHistory and UserSession, run this SQL directly:

```bash
mysql -u morgan -p lcaim
```

Then in the MySQL prompt:

```sql
-- Check current structure
DESCRIBE students_usersession;

-- If session_key column is missing, drop and recreate the table
DROP TABLE IF EXISTS students_usersession;

CREATE TABLE `students_usersession` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `session_key` varchar(40) NOT NULL UNIQUE,
  `ip_address` char(39) DEFAULT NULL,
  `user_agent` longtext NOT NULL,
  `login_time` datetime(6) NOT NULL,
  `last_activity` datetime(6) NOT NULL,
  `user_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `session_key` (`session_key`),
  KEY `students_usersession_user_id_fk` (`user_id`),
  CONSTRAINT `students_usersession_user_id_fk` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Exit MySQL
EXIT;
```

### Option 3: Fresh Start (Simplest)

If you don't need to keep any login history or session tracking data:

```bash
# Activate virtual environment
source .venv/bin/activate

# Drop both tables
mysql -u morgan -p lcaim -e "DROP TABLE IF EXISTS students_usersession; DROP TABLE IF EXISTS students_loginhistory;"

# Re-run migration
python manage.py migrate students
```

## After Running the Fix

Restart your Django development server and the error should be resolved.
