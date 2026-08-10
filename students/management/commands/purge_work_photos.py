"""Delete student work photos past their retention date.

Students are told their photos are deleted after 90 days, so something has to
actually do it. Wire this to a daily scheduled task in production.

    python manage.py purge_work_photos --dry-run
    python manage.py purge_work_photos

Also sweeps abandoned slots: a row is created when the QR is shown, so a
student who never takes the photo leaves one behind with no image at all.
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from students.models import WorkSubmission

# A slot older than this with no photo was never used. Generous next to the
# 15-minute upload token, so nothing in flight is ever caught.
ABANDONED_SLOT_HOURS = 24


class Command(BaseCommand):
    help = "Delete work photos past their retention date, and abandoned upload slots."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true",
                            help="Report what would be deleted, delete nothing")

    def handle(self, *args, **options):
        dry = options["dry_run"]
        now = timezone.now()

        expired = WorkSubmission.objects.filter(purge_after__lte=now)
        abandoned = WorkSubmission.objects.filter(
            status=WorkSubmission.Status.AWAITING_PHOTO,
            created_at__lte=now - timedelta(hours=ABANDONED_SLOT_HOURS),
        )

        for label, qs in (("past retention", expired), ("abandoned slots", abandoned)):
            count = qs.count()
            if not count:
                self.stdout.write(f"{label}: nothing to delete")
                continue
            if dry:
                self.stdout.write(self.style.WARNING(f"{label}: would delete {count}"))
                continue
            # Deleted one at a time so post_delete fires per row and each file
            # is removed. The queryset is materialised first: deleting rows
            # while streaming a cursor over the same rows can skip some.
            removed = 0
            for submission in list(qs):
                submission.delete()
                removed += 1
            self.stdout.write(self.style.SUCCESS(f"{label}: deleted {removed}"))
