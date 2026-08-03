from django.core.management.base import BaseCommand

from homework.models import HomeworkAssignment


class Command(BaseCommand):
    help = (
        "Remove redundant individual student assignments that are already covered "
        "by an assigned class. Historically the admin copied class members into "
        "assigned_students on save; class membership is resolved dynamically, so "
        "these copies only cause stale assignments when a student leaves a class."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help="Show what would be removed without changing anything",
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        total_removed = 0

        assignments = HomeworkAssignment.objects.prefetch_related(
            'assigned_classes__students', 'assigned_students'
        )
        for assignment in assignments:
            class_students = set()
            for teacher_class in assignment.assigned_classes.all():
                class_students.update(teacher_class.students.all())

            redundant = [
                student for student in assignment.assigned_students.all()
                if student in class_students
            ]
            if redundant:
                total_removed += len(redundant)
                names = ', '.join(s.username for s in redundant)
                self.stdout.write(f"{assignment.title}: {len(redundant)} redundant ({names})")
                if not dry_run:
                    assignment.assigned_students.remove(*redundant)

        verb = "Would remove" if dry_run else "Removed"
        self.stdout.write(self.style.SUCCESS(
            f"{verb} {total_removed} redundant individual assignment(s)"
        ))
