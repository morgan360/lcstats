"""
Django management command to create database backups.

Usage:
    python manage.py backup_database
    python manage.py backup_database --compress
    python manage.py backup_database --keep-days 60
"""

import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings


class Command(BaseCommand):
    help = 'Creates a backup of the MySQL database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--backup-dir',
            type=str,
            default=None,
            help='Directory to store backups (default: project_root/backups)',
        )
        parser.add_argument(
            '--compress',
            action='store_true',
            help='Compress the backup file with gzip',
        )
        parser.add_argument(
            '--keep-days',
            type=int,
            default=30,
            help='Number of days to keep old backups (default: 30)',
        )

    def handle(self, *args, **options):
        # Get database settings from Django
        db_settings = settings.DATABASES['default']

        if db_settings['ENGINE'] != 'django.db.backends.mysql':
            raise CommandError('This command only supports MySQL databases')

        db_name = db_settings['NAME']
        db_user = db_settings['USER']
        db_password = db_settings['PASSWORD']
        db_host = db_settings.get('HOST', 'localhost')
        db_port = db_settings.get('PORT', '3306')

        # Set up backup directory
        if options['backup_dir']:
            backup_dir = Path(options['backup_dir'])
        else:
            backup_dir = Path(settings.BASE_DIR) / 'backups'

        backup_dir.mkdir(parents=True, exist_ok=True)

        # Create timestamped backup filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = backup_dir / f'{db_name}_backup_{timestamp}.sql'

        self.stdout.write(f'Creating backup of database: {db_name}')
        self.stdout.write(f'Backup location: {backup_file}')

        # Build mysqldump command
        cmd = [
            'mysqldump',
            f'--host={db_host}',
            f'--port={db_port}',
            f'--user={db_user}',
            f'--password={db_password}',
            '--single-transaction',  # For InnoDB tables
            '--quick',               # Faster for large tables
            '--lock-tables=false',   # Don't lock tables
            db_name
        ]

        try:
            # Execute mysqldump
            with open(backup_file, 'w') as f:
                result = subprocess.run(
                    cmd,
                    stdout=f,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=True
                )

            # Check if backup file was created and has content
            if backup_file.exists() and backup_file.stat().st_size > 0:
                size_mb = backup_file.stat().st_size / (1024 * 1024)
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ Backup successful: {backup_file} ({size_mb:.2f} MB)'
                    )
                )

                # Compress if requested
                if options['compress']:
                    self.stdout.write('Compressing backup...')
                    subprocess.run(['gzip', str(backup_file)], check=True)
                    compressed_file = Path(str(backup_file) + '.gz')
                    if compressed_file.exists():
                        compressed_size_mb = compressed_file.stat().st_size / (1024 * 1024)
                        self.stdout.write(
                            self.style.SUCCESS(
                                f'✓ Compressed: {compressed_file} ({compressed_size_mb:.2f} MB)'
                            )
                        )

                # Clean up old backups
                keep_days = options['keep_days']
                if keep_days > 0:
                    self._cleanup_old_backups(backup_dir, db_name, keep_days)

            else:
                raise CommandError('Backup file was not created or is empty')

        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else str(e)
            raise CommandError(f'Backup failed: {error_msg}')
        except Exception as e:
            raise CommandError(f'Unexpected error: {str(e)}')

    def _cleanup_old_backups(self, backup_dir, db_name, keep_days):
        """Remove backup files older than keep_days"""
        cutoff_date = datetime.now() - timedelta(days=keep_days)
        pattern = f'{db_name}_backup_*.sql*'

        deleted_count = 0
        for backup_file in backup_dir.glob(pattern):
            # Get file modification time
            file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)

            if file_time < cutoff_date:
                backup_file.unlink()
                deleted_count += 1
                self.stdout.write(f'Deleted old backup: {backup_file.name}')

        if deleted_count > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ Cleaned up {deleted_count} old backup(s)'
                )
            )