"""Index the exercises in each solutions PDF, so a teacher can pick one by name.

    python manage.py index_hw_solutions            # only the ones not yet done
    python manage.py index_hw_solutions --force    # redo them all
    python manage.py index_hw_solutions --id 1     # just one

Safe to re-run: without --force it skips anything already indexed.
"""
from django.core.management.base import BaseCommand

from hw_solutions.models import HWSolution
from hw_solutions.services import build_sections


class Command(BaseCommand):
    help = "Detect the exercises in each HW solutions PDF and cache their page ranges."

    def add_arguments(self, parser):
        parser.add_argument("--id", type=int, help="Index only this solution")
        parser.add_argument("--force", action="store_true",
                            help="Re-index solutions that already have sections")

    def handle(self, *args, **options):
        qs = HWSolution.objects.exclude(pdf_file="")
        if options["id"]:
            qs = qs.filter(pk=options["id"])

        for solution in qs:
            try:
                sections = build_sections(solution, force=options["force"])
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"[{solution.pk}] {solution.title}: {e}"))
                continue

            if not sections:
                self.stdout.write(self.style.WARNING(
                    f"[{solution.pk}] {solution.title}: no exercises found — "
                    "teachers will type a page range by hand for this one."
                ))
                continue

            self.stdout.write(self.style.SUCCESS(
                f"[{solution.pk}] {solution.title}: {len(sections)} exercise(s)"))
            for s in sections:
                self.stdout.write(f"      {s.label}: pages {s.page_range} ({s.page_count}pp)")
