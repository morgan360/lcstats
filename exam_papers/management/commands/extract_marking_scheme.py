"""
Management command to extract marking scheme pages from PDF and associate with questions.
"""
from django.core.management.base import BaseCommand
from exam_papers.models import ExamPaper, ExamQuestion, MarkingScheme
from exam_papers.utils import extract_pdf_pages_as_images
import os


class Command(BaseCommand):
    help = 'Extract marking scheme pages from PDF and link to questions'

    def add_arguments(self, parser):
        parser.add_argument(
            'paper_id',
            type=int,
            help='ID of the ExamPaper'
        )
        parser.add_argument(
            '--preview',
            action='store_true',
            help='Preview PDF structure without extracting'
        )
        parser.add_argument(
            '--page-ranges',
            type=str,
            help='Comma-separated list of question:page_range pairs (e.g., "1:1-2,2:3-4,3:5-6")'
        )

    def handle(self, *args, **options):
        paper_id = options['paper_id']
        preview_only = options.get('preview', False)
        page_ranges_str = options.get('page_ranges')

        try:
            paper = ExamPaper.objects.get(id=paper_id)
        except ExamPaper.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'ExamPaper with ID {paper_id} not found'))
            return

        if not paper.marking_scheme_pdf:
            self.stdout.write(self.style.ERROR('No marking scheme PDF uploaded for this paper'))
            self.stdout.write('Please upload a marking scheme PDF in the admin first.')
            return

        pdf_path = paper.marking_scheme_pdf.path

        if not os.path.exists(pdf_path):
            self.stdout.write(self.style.ERROR(f'Marking scheme PDF file not found at {pdf_path}'))
            return

        # Preview mode
        if preview_only:
            self.stdout.write(self.style.SUCCESS(f'\n=== Marking Scheme PDF Info for {paper} ==='))
            try:
                import fitz  # PyMuPDF
                doc = fitz.open(pdf_path)
                self.stdout.write(f'Total pages: {len(doc)}')
                self.stdout.write(f'Metadata: {doc.metadata}')
                self.stdout.write('\nPage details:')
                for i, page in enumerate(doc, 1):
                    rect = page.rect
                    self.stdout.write(f'  Page {i}: {rect.width}x{rect.height} pts')
                doc.close()
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error reading PDF: {str(e)}'))
            return

        # Parse page ranges
        if not page_ranges_str:
            self.stdout.write(self.style.ERROR('--page-ranges is required for extraction'))
            self.stdout.write('\nExample usage:')
            self.stdout.write('  python manage.py extract_marking_scheme <paper_id> --page-ranges "1:1-2,2:3-4,3:5-6"')
            self.stdout.write('\nFormat: question_number:start_page-end_page')
            return

        page_ranges = {}
        for pair in page_ranges_str.split(','):
            try:
                q_num, pages = pair.split(':')
                start, end = pages.split('-')
                page_ranges[int(q_num)] = (int(start), int(end))
            except ValueError:
                self.stdout.write(self.style.ERROR(f'Invalid page range format: {pair}'))
                return

        self.stdout.write(self.style.SUCCESS(f'\n=== Extracting Marking Scheme for {paper} ==='))
        self.stdout.write(f'PDF: {pdf_path}')
        self.stdout.write(f'Questions to process: {len(page_ranges)}')

        # Extract marking scheme pages for each question
        for question_num, (start_page, end_page) in page_ranges.items():
            try:
                # Get the question
                question = paper.questions.get(question_number=question_num)

                self.stdout.write(f'\nProcessing Q{question_num} (pages {start_page}-{end_page})...')

                # Extract pages as image
                image_path = extract_pdf_pages_as_images(
                    pdf_path,
                    start_page,
                    end_page,
                    output_prefix=f'marking_scheme_q{question_num}'
                )

                if image_path:
                    # For each question part, create/update marking scheme with image reference
                    parts = question.parts.all()
                    self.stdout.write(f'  Found {parts.count()} parts for Q{question_num}')

                    for part in parts:
                        # Get or create marking scheme
                        marking_scheme, created = MarkingScheme.objects.get_or_create(
                            question_part=part,
                            defaults={
                                'marking_breakdown': {
                                    'steps': [],
                                    'common_errors': [],
                                    'partial_credit_notes': 'See marking scheme image'
                                },
                                'examiner_notes': f'Marking scheme extracted from PDF pages {start_page}-{end_page}'
                            }
                        )

                        # Store reference to marking scheme image
                        # (We'll store the path in examiner_notes for now)
                        if created:
                            marking_scheme.examiner_notes = f'Marking scheme image: {image_path}\nPages {start_page}-{end_page}'
                            marking_scheme.save()
                            self.stdout.write(self.style.SUCCESS(f'    ✓ Created marking scheme for {part.label}'))
                        else:
                            self.stdout.write(self.style.WARNING(f'    ⚠ Marking scheme already exists for {part.label}'))

                    self.stdout.write(self.style.SUCCESS(f'  ✓ Processed Q{question_num}'))
                else:
                    self.stdout.write(self.style.ERROR(f'  ✗ Failed to extract pages for Q{question_num}'))

            except ExamQuestion.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'  ✗ Question {question_num} not found in database'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✗ Error processing Q{question_num}: {str(e)}'))

        self.stdout.write(self.style.SUCCESS('\n=== Marking Scheme Extraction Complete ==='))
        self.stdout.write('\nNext steps:')
        self.stdout.write('1. Review marking schemes in admin: /admin/exam_papers/markingscheme/')
        self.stdout.write('2. Add detailed marking breakdown JSON for each part')
        self.stdout.write('3. Add examiner notes and partial credit guidelines')