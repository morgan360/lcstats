# Database Backup Setup for PythonAnywhere

## Django Management Command

A new management command has been created: `backup_database`

### Usage

```bash
# Basic backup
python manage.py backup_database

# Compressed backup
python manage.py backup_database --compress

# Keep backups for 60 days instead of default 30
python manage.py backup_database --keep-days 60

# Custom backup directory
python manage.py backup_database --backup-dir /home/username/db_backups
```

### Features

- ✓ Automatically uses Django database settings (no need to configure credentials)
- ✓ Creates timestamped backups: `lcaim_backup_YYYYMMDD_HHMMSS.sql`
- ✓ Optional gzip compression to save space
- ✓ Automatic cleanup of old backups (default: 30 days)
- ✓ Backup directory created automatically if it doesn't exist
- ✓ Safe for live databases (uses `--single-transaction` and `--lock-tables=false`)

## Setting Up on PythonAnywhere EU

### 1. Deploy the New Command

Upload the new management command to your PythonAnywhere project:
- `students/management/commands/backup_database.py`
- Ensure `students/management/__init__.py` exists
- Ensure `students/management/commands/__init__.py` exists

### 2. Test the Command

SSH into PythonAnywhere and test:

```bash
cd /home/YOUR_USERNAME/lcstats
python manage.py backup_database --compress
```

This should create a backup in `/home/YOUR_USERNAME/lcstats/backups/`

### 3. Schedule Daily Backups

1. Go to **PythonAnywhere Dashboard** → **Tasks** tab
2. Click **"Create a new scheduled task"**
3. Enter this command:

```bash
cd /home/YOUR_USERNAME/lcstats && /home/YOUR_USERNAME/.virtualenvs/YOUR_VENV/bin/python manage.py backup_database --compress
```

4. Set the time (e.g., `02:00` for 2:00 AM daily)
5. Click **"Create"**

### 4. Alternative: Use the working directory approach

```bash
/home/YOUR_USERNAME/.virtualenvs/YOUR_VENV/bin/python /home/YOUR_USERNAME/lcstats/manage.py backup_database --compress --backup-dir /home/YOUR_USERNAME/backups
```

## Backup Storage Locations

**Default location:** `/home/YOUR_USERNAME/lcstats/backups/`

**Custom location example:**
```bash
python manage.py backup_database --backup-dir /home/YOUR_USERNAME/db_backups
```

## Monitoring Backups

Check if backups are being created:

```bash
ls -lh /home/YOUR_USERNAME/lcstats/backups/
```

View the scheduled task log in PythonAnywhere's Tasks tab to see success/failure messages.

## Backup Size Estimates

- Uncompressed: Varies based on data (typically 1-100 MB for small projects)
- Compressed (gzip): Usually 10-20% of original size

## Restoring from Backup

To restore a backup:

```bash
# Unzip if compressed
gunzip lcaim_backup_20260118_120000.sql.gz

# Restore to database
mysql -h YOUR_USERNAME.mysql.eu.pythonanywhere-services.com \
      -u YOUR_USERNAME \
      -p \
      lcaim < lcaim_backup_20260118_120000.sql
```

## Downloading Backups Locally

From your local machine:

```bash
scp YOUR_USERNAME@eu.pythonanywhere.com:/home/YOUR_USERNAME/lcstats/backups/lcaim_backup_*.sql.gz ./local_backups/
```

## Troubleshooting

**Command not found:**
- Ensure the files are uploaded to the correct location
- Check that `__init__.py` files exist in the management directories

**Permission denied:**
- Ensure the backup directory is writable
- On PythonAnywhere, use paths in your home directory: `/home/YOUR_USERNAME/`

**Database connection error:**
- Verify Django settings are correct on PythonAnywhere
- Check that `settings.py` has the correct database credentials

**mysqldump not found:**
- On PythonAnywhere, `mysqldump` should be available by default
- Try using the full path: `/usr/bin/mysqldump`