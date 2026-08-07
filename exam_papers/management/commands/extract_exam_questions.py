# exam_papers/management/commands/extract_exam_questions.py
"""
Management command to extract question images from an exam paper PDF.
Creates ExamQuestion records with images for manual completion.
"""
from django.core.management.base import BaseCommand, CommandError
from django.core.files.base import ContentFile
from exam_papers.models import ExamPaper, ExamQuestion, ExamQuestionPart
from exam_papers.utils import (
    detect_question_layout, detect_legacy_question_layout, extract_pdf_regions,
    extract_pdf_page_ranges, split_pdf_into_questions, get_pdf_info,
    parse_part_label,
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
        parser.add_argument(
            '--legacy',
            action='store_true',
            help='For papers before 2012 Paper 2, which number questions "1." '
                 'and fit two to a page: detect each question as a region of a '
                 'page and crop it out, instead of using whole pages'
        )
        parser.add_argument(
            '--refresh-images',
            action='store_true',
            help='Re-render question images that are already set (default: only '
                 'fill in questions that have no image)'
        )

    def handle(self, *args, **options):
        paper_id = options['paper_id']
        num_questions = options.get('num_questions')
        page_ranges_str = options.get('page_ranges')
        preview = options.get('preview', False)
        dry_run = options.get('dry_run', False)
        refresh_images = options.get('refresh_images', False)

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

        if options.get('auto') or options.get('legacy'):
            legacy = options.get('legacy', False)

            if legacy:
                layout = detect_legacy_question_layout(pdf_path)
                if not layout:
                    raise CommandError(
                        'No "1." style question numbers found in the PDF text '
                        'layer. Try --auto, which reads the "Question N" '
                        'headings used from 2012 Paper 2 onwards.'
                    )
            else:
                layout = detect_question_layout(pdf_path)
                if not layout:
                    raise CommandError(
                        'No "Question N" headings found in the PDF text layer. '
                        'Papers before 2012 Paper 2 use a different layout - '
                        'try --legacy, or --page-ranges to place them by hand.'
                    )

            self.stdout.write(self.style.SUCCESS(f'\n=== Detected structure for {paper} ==='))
            for item in layout:
                parts = ', '.join(f"({p})" for p in item['parts']) or '(none found)'
                marks = item['marks'] if item['marks'] is not None else '?'
                if legacy:
                    where = (f"page {item['start_page']} "
                             f"y {item['clip'][1]:.0f}-{item['clip'][3]:.0f}")
                else:
                    where = f"pages {item['start_page']}-{item['end_page']}"
                self.stdout.write(
                    f"  Question {item['question']:<3} {where}  "
                    f"{marks} marks  parts: {parts}"
                )

            if dry_run:
                self.stdout.write(self.style.WARNING(
                    '\nDry run: nothing written. Re-run without --dry-run to apply.'
                ))
                return

            if legacy:
                question_images = extract_pdf_regions(pdf_path, layout)
            else:
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
                'Must specify --auto, --legacy, --num-questions or --page-ranges. '
                'Use --preview to see PDF structure first, or --auto --dry-run '
                'to see what can be detected automatically. Papers before 2012 '
                'Paper 2 need --legacy.'
            )

        # Create ExamQuestion records with images
        created_count = 0
        updated_count = 0
        parts_created = 0
        left_alone = 0

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

            # An image already there may have been cropped or replaced by hand,
            # so only fill a gap unless asked to refresh.
            if not question.image or refresh_images:
                image_filename = f'{paper.slug}_q{question_num}.png'
                question.image.save(image_filename, ContentFile(img_data), save=True)
                image_note = 'image' if created else 'image refreshed'
            else:
                image_note = 'image kept'

            # Fill in what the text layer told us, but never overwrite work
            # already done by hand.
            detected = next((i for i in layout if i['question'] == question_num), None)
            if detected:
                if detected['marks'] and not question.total_marks:
                    question.total_marks = detected['marks']
                    question.save(update_fields=['total_marks'])
                    self.stdout.write(f'    marks: {detected["marks"]}')

                # Detection only sees top-level labels - (a), (b), (c) - while
                # parts entered by hand are often finer, like "(b) (i)" and
                # "(b) (ii)". Comparing the written label would not recognise
                # those as the same part and would add a spurious "(b)" beside
                # them, so compare the letter each label means. That skips
                # letters already covered without skipping the whole question,
                # which would leave a half-entered question half-entered.
                existing = set()
                for part in question.parts.all():
                    parsed = parse_part_label(part.label)
                    if parsed:
                        existing.add(parsed[0])

                if existing:
                    left_alone += 1
                    self.stdout.write(
                        f'    parts: ({"), (".join(sorted(existing))}) already entered'
                    )

                for order, letter in enumerate(detected['parts'], start=1):
                    if letter in existing:
                        continue
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
                    self.style.SUCCESS(f'✓ Created Question {question_num} ({image_note})')
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'⟳ Question {question_num} ({image_note})')
                )

        # Summary
        self.stdout.write(self.style.SUCCESS(f'\n=== Extraction Complete ==='))
        self.stdout.write(f'Exam Paper: {paper}')
        self.stdout.write(f'Created: {created_count} questions')
        self.stdout.write(f'Parts created: {parts_created}')
        self.stdout.write(f'Updated: {updated_count} questions')
        self.stdout.write(f'Left alone (parts already entered): {left_alone} questions')
        self.stdout.write(
            self.style.SUCCESS(
                f'\nNext steps in /admin/exam_papers/examquestion/:\n'
                f'   - Topic classification (not detectable from the PDF)\n'
                f'   - Split any part that has sub-parts, e.g. (b) into (b) (i) and (b) (ii)\n'
                f'   - Marking scheme crop into each part\'s solution image, then\n'
                f'     auto_extract_marking_info to fill in per-part marks\n'
            )
        )