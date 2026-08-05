# exam_papers/management/commands/extract_exam_questions.py
"""
Management command to extract question images from an exam paper PDF.
Creates ExamQuestion records with images for manual completion.
"""
from django.core.management.base import BaseCommand, CommandError
from django.core.files.base import ContentFile
from exam_papers.models import ExamPaper, ExamQuestion, ExamQuestionPart
from exam_papers.utils import (
    detect_question_layout, extract_pdf_page_ranges, split_pdf_into_questions,
    get_pdf_info,
)
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
        parser.add_argument(
            '--auto',
            action='store_true',
            help="Read page ranges, marks and part labels from the PDF's text "
                 "layer instead of passing --page-ranges by hand"
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what --auto detected without writing anything'
        )

    def handle(self, *args, **options):
        paper_id = options['paper_id']
        num_questions = options.get('num_questions')
        page_ranges_str = options.get('page_ranges')
        preview = options.get('preview', False)
        dry_run = options.get('dry_run', False)

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
        layout = []

        if options.get('auto'):
            layout = detect_question_layout(pdf_path)
            if not layout:
                raise CommandError(
                    'No "Question N" headings found in the PDF text layer. '
                    'Papers before 2012 Paper 2 use a different layout - use '
                    '--page-ranges for those.'
                )

            self.stdout.write(self.style.SUCCESS(f'\n=== Detected structure for {paper} ==='))
            for item in layout:
                parts = ', '.join(f"({p})" for p in item['parts']) or '(none found)'
                marks = item['marks'] if item['marks'] is not None else '?'
                self.stdout.write(
                    f"  Question {item['question']:<3} pages "
                    f"{item['start_page']}-{item['end_page']}  "
                    f"{marks} marks  parts: {parts}"
                )

            if dry_run:
                self.stdout.write(self.style.WARNING(
                    '\nDry run: nothing written. Re-run without --dry-run to apply.'
                ))
                return

            page_ranges = [(i['question'], i['start_page'], i['end_page']) for i in layout]
            question_images = extract_pdf_page_ranges(pdf_path, page_ranges)

        elif page_ranges_str:
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
                'Must specify --auto, --num-questions or --page-ranges. '
                'Use --preview to see PDF structure first, or --auto --dry-run '
                'to see what can be detected automatically.'
            )

        # Create ExamQuestion records with images
        created_count = 0
        updated_count = 0
        parts_created = 0

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

            # Fill in what the text layer told us, but never overwrite work
            # already done by hand.
            detected = next((i for i in layout if i['question'] == question_num), None)
            if detected:
                if detected['marks'] and not question.total_marks:
                    question.total_marks = detected['marks']
                    question.save(update_fields=['total_marks'])
                    self.stdout.write(f'    marks: {detected["marks"]}')

                for order, letter in enumerate(detected['parts'], start=1):
                    label = f'({letter})'
                    _, part_created = ExamQuestionPart.objects.get_or_create(
                        question=question,
                        label=label,
                        defaults={'order': order, 'max_marks': 0},
                    )
                    if part_created:
                        parts_created += 1
                        self.stdout.write(f'    part {label}')

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
        self.stdout.write(f'Parts created: {parts_created}')
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