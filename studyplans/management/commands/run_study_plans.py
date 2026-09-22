"""Nightly upkeep for study plans."""
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from studyplans.services import nightly


class Command(BaseCommand):
    help = """Mark finished work, award MicroBadges, open and grade Badge Tests,
and tell the teacher about topics that have fallen behind.

Run this nightly from cron. There is no background queue in this project, so
cron is how a plan gets to do anything between page loads -- without it a
Badge Test never opens on its own and a stalled topic is never flagged.

Everything it does is safe to repeat: work already counted is not counted again,
a MicroBadge is earned once, and a decided Badge Test is not re-marked.
Running it twice in one day is a no-op the second time.

It will never delete an item or move one; work that is no longer needed is
marked skipped, and anything it cannot decide is flagged for
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

        totals = {'completed': 0, 'earned': 0, 'unlocked': 0, 'graded': 0,
                  'behind': 0, 'closed': 0}

        for plan in plans:
            summary = nightly.run_for_plan(plan, today=today, dry_run=dry_run)
            for key in ('completed', 'earned', 'unlocked', 'graded', 'behind'):
                totals[key] += summary[key]
            totals['closed'] += 1 if summary['closed'] else 0

            if any(summary[k] for k in ('completed', 'earned', 'unlocked',
                                        'graded', 'behind')) or summary['closed']:
                self.stdout.write(
                    f"  {plan.student.username} / {plan.title}: "
                    f"{summary['completed']} done, "
                    f"{summary['earned']} MicroBadge(s), "
                    f"{summary['unlocked']} unlocked, "
                    f"{summary['graded']} marked, "
                    f"{summary['behind']} behind"
                    + (", plan finished" if summary['closed'] else ""))

        self.stdout.write(self.style.SUCCESS(
            f"{totals['completed']} item(s) completed, "
            f"{totals['earned']} MicroBadge(s) earned, "
            f"{totals['unlocked']} Badge Test(s) opened, "
            f"{totals['graded']} marked, "
            f"{totals['behind']} topic(s) flagged as behind, "
            f"{totals['closed']} plan(s) finished."))
