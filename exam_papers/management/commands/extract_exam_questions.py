# exam_papers/management/commands/extract_exam_questions.py
"""
Management command to extract question images from an exam paper PDF.
Creates ExamQuestion records with images for manual completion.
"""
from django.core.management.base import BaseCommand, CommandError
from django.core.files.base import ContentFile
from exam_papers.models import ExamPaper, ExamQuestion
from exam_papers.utils import extract_pdf_page_ranges, split_pdf_into_questions, get_pdf_info
import os


class Command(BaseCommand):
    help = 'Extract question images from an exam paper PDF'

    def add_arguments(self, parser):
        parser.add_argument(
            'paper_id',
            type=int,
            help='ID of the ExamPaper to extract questions from'
        )
        parser.add_argument(
            '--num-questions',
            type=int,
            help='Number of questions in the paper (for automatic splitting)'
        )
        parser.add_argument(
            '--page-ranges',
            type=str,
            help='Page ranges for each question. Format: "1:1-1,2:2-3,3:4-4" (question:start-end)'
        )
        parser.add_argument(
            '--preview',
            action='store_true',
            help='Preview PDF info without extracting'
        )

    def handle(self, *args, **options):
        paper_id = options['paper_id']
        num_questions = options.get('num_questions')
        page_ranges_str = options.get('page_ranges')
        preview = options.get('preview', False)

        # Get the exam paper
        try:
            paper = ExamPaper.objects.get(id=paper_id)
        except ExamPaper.DoesNotExist:
            raise CommandError(f'ExamPaper with id {paper_id} does not exist')

        # Check if PDF exists
        if not paper.source_pdf:
            raise CommandError(f'ExamPaper {paper} has no source PDF uploaded')

        pdf_path = paper.source_pdf.path

        # Preview mode - just show PDF info
        if preview:
            self.stdout.write(self.style.SUCCESS(f'\n=== PDF Info for {paper} ==='))
            info = get_pdf_info(pdf_path)
            self.stdout.write(f"Total pages: {info['page_count']}")
            self.stdout.write(f"Metadata: {info['metadata']}")
            self.stdout.write("\nPage details:")
            for page in info['pages']:
                self.stdout.write(f"  Page {page['number']}: {page['width']}x{page['height']} pts")
            return

        # Extract questions
        question_images = []

        if page_ranges_str:
            # Parse page ranges
            # Format: "1:1-1,2:2-3,3:4-4"
            page_ranges = []
            for item in page_ranges_str.split(','):
                q_num, pages = item.split(':')
                start, end = pages.split('-')
                page_ranges.append((int(q_num), int(start), int(end)))

            self.stdout.write(f'Extracting questions using page ranges: {page_ranges}')
            question_images = extract_pdf_page_ranges(pdf_path, page_ranges)

        elif num_questions:
            # Automatic splitting
            self.stdout.write(f'Automatically splitting PDF into {num_questions} questions')
            question_images = split_pdf_into_questions(pdf_path, num_questions)

        else:
            raise CommandError(
                'Must specify either --num-questions or --page-ranges. '
                'Use --preview to see PDF structure first.'
            )

        # Create ExamQuestion records with images
        created_count = 0
        updated_count = 0

        for question_num, img_data in question_images:
            # Check if question already exists
            question, created = ExamQuestion.objects.get_or_create(
                exam_paper=paper,
                question_number=question_num,
                defaults={
                    'title': f'Question {question_num}',
                    'total_marks': 0,  # To be filled manually
                    'order': question_num
                }
            )

            # Save the image
            image_filename = f'{paper.slug}_q{question_num}.png'
            question.image.save(image_filename, ContentFile(img_data), save=True)

            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created Question {question_num}')
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'⟳ Updated image for Question {question_num}')
                )

        # Summary
        self.stdout.write(self.style.SUCCESS(f'\n=== Extraction Complete ==='))
        self.stdout.write(f'Exam Paper: {paper}')
        self.stdout.write(f'Created: {created_count} questions')
        self.stdout.write(f'Updated: {updated_count} questions')
        self.stdout.write(
            self.style.SUCCESS(
                f'\nNext steps:\n'
                f'1. Go to Django admin: /admin/exam_papers/examquestion/\n'
                f'2. Edit each question to add:\n'
                f'   - Stem text (if needed)\n'
                f'   - Topic classification\n'
                f'   - Total marks\n'
                f'   - Suggested time\n'
                f'   - Question parts (a), (b), (c) with answers and solutions\n'
            )
        )