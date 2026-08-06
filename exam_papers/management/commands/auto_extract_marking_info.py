"""
Management command to read per-part mark allocations off the marking scheme
crops attached to question parts, using the vision model.

Marks are the one piece of the marking scheme the database actually stores, so
that is all this extracts. Worked solutions stay as the scheme image itself -
see the note in exam_papers/models.py on why exam content is not held as text.
"""
from django.core.management.base import BaseCommand, CommandError
from exam_papers.models import ExamPaper
from exam_papers.services.vision_grading import extract_max_marks_from_scheme


class Command(BaseCommand):
    help = "Fill in question part max_marks from their marking scheme images"

    def add_arguments(self, parser):
        parser.add_argument(
            'paper_id',
            type=int,
            help='ID of the ExamPaper'
        )
        parser.add_argument(
            '--question',
            type=int,
            help='Process only a specific question number (optional)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what was read without saving to database'
        )
        parser.add_argument(
            '--overwrite',
            action='store_true',
            help='Also replace marks that are already set (default: fill blanks only)'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        overwrite = options['overwrite']

        try:
            paper = ExamPaper.objects.get(id=options['paper_id'])
        except ExamPaper.DoesNotExist:
            raise CommandError(f"ExamPaper with ID {options['paper_id']} not found")

        questions = paper.questions.all()
        if options.get('question'):
            questions = questions.filter(question_number=options['question'])

        self.stdout.write(self.style.SUCCESS(f'\n=== Reading marks for {paper} ==='))
        if dry_run:
            self.stdout.write(self.style.WARNING('Dry run - nothing will be saved'))

        read = skipped = saved = 0

        for question in questions.order_by('order'):
            self.stdout.write(f'\n--- Question {question.question_number} ---')

            for part in question.parts.all().order_by('order'):
                # The marking scheme crop lives on the part; without one there
                # is nothing to read.
                if not part.solution_image:
                    self.stdout.write(
                        self.style.WARNING(f'  {part.label}: no marking scheme image, skipping')
                    )
                    skipped += 1
                    continue

                if part.max_marks and not overwrite:
                    self.stdout.write(
                        f'  {part.label}: already {part.max_marks} marks, leaving alone'
                    )
                    skipped += 1
                    continue

                marks = extract_max_marks_from_scheme(part.solution_image, part.label)
                if marks is None:
                    self.stdout.write(
                        self.style.ERROR(f'  {part.label}: could not read marks')
                    )
                    continue

                read += 1
                self.stdout.write(self.style.SUCCESS(f'  {part.label}: {marks} marks'))

                if not dry_run:
                    part.max_marks = marks
                    part.save(update_fields=['max_marks'])
                    saved += 1

        self.stdout.write(self.style.SUCCESS('\n=== Done ==='))
        self.stdout.write(f'Read: {read}   Saved: {saved}   Skipped: {skipped}')
        if dry_run and read:
            self.stdout.write(
                self.style.WARNING('Re-run without --dry-run to save these marks.')
            )
        if saved:
            self.stdout.write(
                'Vision misreads marks sometimes - check them in admin before publishing.'
            )
