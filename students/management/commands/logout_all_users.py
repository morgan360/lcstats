# students/management/commands/logout_all_users.py
from django.core.management.base import BaseCommand
from django.contrib.sessions.models import Session
from django.utils import timezone


class Command(BaseCommand):
    help = 'Logs out all users by clearing all active sessions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        # Get all active sessions (not expired)
        now = timezone.now()
        active_sessions = Session.objects.filter(expire_date__gte=now)
        session_count = active_sessions.count()

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'[DRY RUN] Would delete {session_count} active session(s)'
                )
            )
        else:
            # Delete all sessions (this logs out all users)
            active_sessions.delete()

            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully logged out all users by deleting {session_count} session(s)'
                )
            )

        # Also clean up expired sessions
        expired_sessions = Session.objects.filter(expire_date__lt=now)
        expired_count = expired_sessions.count()

        if expired_count > 0:
            if dry_run:
                self.stdout.write(
                    self.style.WARNING(
                        f'[DRY RUN] Would also delete {expired_count} expired session(s)'
                    )
                )
            else:
                expired_sessions.delete()
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Also cleaned up {expired_count} expired session(s)'
                    )
                )