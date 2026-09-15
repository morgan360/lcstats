"""Delete homework-check photos past their retention date, keeping the reports.

These are photographs of named children's work, so something has to actually
remove them rather than leaving them on disk forever. Wire this to a daily
scheduled task in production.

    python manage.py purge_homework_checks --dry-run
    python manage.py purge_homework_checks

A check's photos go once the newest of them is older than
HOMEWORK_CHECK_PHOTO_RETENTION_DAYS. The check itself -- the marked report, the
teacher's edits, the rating -- is kept as the student's history; only a teacher
deleting it removes that.

Also sweeps abandoned checks: a row is created when the teacher names the
exercise, so one started and never photographed leaves a check with no photos.
A check whose photos were purged before it was ever marked lands here too,
which is right -- with no report and no photos there is nothing left in it.

And emailed scans nobody claimed: they are the same photographs, only not yet
matched to a student, so they get the same retention.

Note: PythonAnywhere scheduled tasks can only be created through the web UI,
never over SSH, so this has to be added by hand there.
"""
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Max
from django.utils import timezone

from homework_check.models import HomeworkCheck, InboundScan

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
        days = getattr(settings, "HOMEWORK_CHECK_PHOTO_RETENTION_DAYS", 7)

        # Keyed on the newest photo, not the check's age, so photos added to an
        # old draft still get their full retention before anyone marks them.
        expired = (
            HomeworkCheck.objects
            .annotate(newest_photo=Max("photos__created_at"))
            .filter(newest_photo__lte=now - timedelta(days=days))
        )
        abandoned = HomeworkCheck.objects.filter(
            status=HomeworkCheck.Status.DRAFT,
            created_at__lte=now - timedelta(hours=ABANDONED_HOURS),
            photos__isnull=True,
        )
        stale_scans = InboundScan.objects.filter(
            received_at__lte=now - timedelta(days=days))

        if dry:
            n_photos = sum(check.photos.count() for check in expired)
            self.stdout.write(
                f"Would delete {n_photos} photo(s) from {expired.count()} "
                f"check(s) older than {days} day(s), keeping their reports, "
                f"{abandoned.count()} abandoned check(s), and "
                f"{stale_scans.count()} unclaimed scan(s)."
            )
            return

        n_checks = n_photos = 0
        for check in expired:
            # One at a time so the post_delete signal fires per photo and the
            # files actually leave the disk -- a queryset delete would skip it.
            count = 0
            for photo in check.photos.all():
                photo.delete()
                count += 1
            check.photos_deleted_at = now
            check.photos_deleted_count += count
            check.save(update_fields=["photos_deleted_at", "photos_deleted_count"])
            n_checks += 1
            n_photos += count

        # Counted after the photo pass on purpose: an unmarked draft that has
        # just lost its photos is now abandoned, and goes tonight rather than
        # sitting there as an empty check until tomorrow.
        n_abandoned = 0
        for check in abandoned:
            check.delete()
            n_abandoned += 1

        # One at a time, again, so the post_delete receiver removes the PDF and
        # its thumbnail from disk.
        n_scans = 0
        for scan in stale_scans:
            scan.delete()
            n_scans += 1

        self.stdout.write(self.style.SUCCESS(
            f"Deleted {n_photos} photo(s) from {n_checks} check(s), keeping their "
            f"reports, {n_abandoned} abandoned check(s), and {n_scans} unclaimed "
            f"scan(s)."
        ))
