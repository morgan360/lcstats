"""Nightly upkeep for study plans."""
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from studyplans.services import nightly


class Command(BaseCommand):
    help = """Mark finished work, open and grade checkpoints, and carry forward
what was missed.

Run this nightly from cron. There is no background queue in this project, so
cron is how a plan gets to do anything between page loads -- without it a
checkpoint never opens on its own and nothing is ever carried forward.

Everything it does is safe to repeat: work already counted is not counted again,
a decided checkpoint is not re-marked, and an item already moved into this week
is left where it is. Running it twice in one day is a no-op the second time.

It will never delete an item or move one a teacher chose by hand; work that is
no longer needed is marked skipped, and anything it cannot decide is flagged for
the teacher instead of guessed at.

    python manage.py run_study_plans --dry-run
    python manage.py run_study_plans
    python manage.py run_study_plans --student aoife
"""

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Report what would change without writing anything')
        parser.add_argument(
            '--plan', type=int, help='Only this plan id')
        parser.add_argument(
            '--student', type=str, help='Only this username')
        parser.add_argument(
            '--date', type=str,
            help='Treat this YYYY-MM-DD as today (for testing)')

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        today = timezone.localdate()
        if options.get('date'):
            try:
                today = datetime.strptime(options['date'], '%Y-%m-%d').date()
            except ValueError:
                raise CommandError("--date must look like 2026-09-20")

        student = None
        if options.get('student'):
            from django.contrib.auth.models import User
            try:
                student = User.objects.get(username=options['student'])
            except User.DoesNotExist:
                raise CommandError(f"No user called {options['student']}")

        plans = nightly.active_plans(student=student, plan_id=options.get('plan'))

        if dry_run:
            self.stdout.write(self.style.WARNING(
                "Dry run: nothing will be written."))
        self.stdout.write(f"Checking {plans.count()} active plan(s) as of {today}.")

        totals = {'completed': 0, 'unlocked': 0, 'graded': 0, 'carried': 0,
                  'closed': 0}

        for plan in plans:
            summary = nightly.run_for_plan(plan, today=today, dry_run=dry_run)
            for key in ('completed', 'unlocked', 'graded', 'carried'):
                totals[key] += summary[key]
            totals['closed'] += 1 if summary['closed'] else 0

            if any(summary[k] for k in ('completed', 'unlocked', 'graded',
                                        'carried')) or summary['closed']:
                self.stdout.write(
                    f"  {plan.student.username} / {plan.title}: "
                    f"{summary['completed']} done, "
                    f"{summary['unlocked']} unlocked, "
                    f"{summary['graded']} marked, "
                    f"{summary['carried']} carried"
                    + (", plan finished" if summary['closed'] else ""))

        self.stdout.write(self.style.SUCCESS(
            f"{totals['completed']} item(s) completed, "
            f"{totals['unlocked']} checkpoint(s) opened, "
            f"{totals['graded']} marked, "
            f"{totals['carried']} carried forward, "
            f"{totals['closed']} plan(s) finished."))
