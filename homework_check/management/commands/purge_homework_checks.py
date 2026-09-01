"""Delete homework-check photos past their retention date.

These are photographs of named children's work, so something has to actually
remove them rather than leaving them on disk forever. Wire this to a daily
scheduled task in production.

    python manage.py purge_homework_checks --dry-run
    python manage.py purge_homework_checks

Also sweeps abandoned checks: a row is created when the teacher names the
exercise, so one started and never photographed leaves a check with no photos.

Note: PythonAnywhere scheduled tasks can only be created through the web UI,
never over SSH, so this has to be added by hand there.
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from homework_check.models import HomeworkCheck

# A check older than this with no photos was never used. Generous, so nothing
# a teacher is part way through is ever caught.
ABANDONED_HOURS = 48


class Command(BaseCommand):
    help = "Delete homework-check photos past their retention date, and abandoned checks."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true",
                            help="Report what would be deleted, delete nothing")

    def handle(self, *args, **options):
        dry = options["dry_run"]
        now = timezone.now()

        expired = HomeworkCheck.objects.filter(purge_after__lte=now)
        abandoned = HomeworkCheck.objects.filter(
            status=HomeworkCheck.Status.DRAFT,
            created_at__lte=now - timedelta(hours=ABANDONED_HOURS),
            photos__isnull=True,
        )

        n_expired = expired.count()
        n_abandoned = abandoned.count()

        if dry:
            self.stdout.write(
                f"Would delete {n_expired} expired check(s) and "
                f"{n_abandoned} abandoned one(s)."
            )
            return

        # Deleted one at a time so the post_delete signal fires per photo and
        # the files actually leave the disk -- a queryset delete would skip it.
        for check in expired:
            check.delete()
        for check in abandoned:
            check.delete()

        self.stdout.write(self.style.SUCCESS(
            f"Deleted {n_expired} expired check(s) and {n_abandoned} abandoned one(s)."
        ))
