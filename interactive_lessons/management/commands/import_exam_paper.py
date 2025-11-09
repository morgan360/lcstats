"""
Management command to import LC exam papers from PDF files.
Usage: python manage.py import_exam_paper <pdf_path> --year 2024 --paper p1
"""
import os
import re
from django.core.management.base import BaseCommand, CommandError
from django.core.files import File
from django.core.files.base import ContentFile
from interactive_lessons.models import Topic, Question, QuestionPart
from PIL import Image
import io

try:
    import PyPDF2
    import pdf2image
    DEPENDENCIES_AVAILABLE = True
except ImportError:
    DEPENDENCIES_AVAILABLE = False


class Command(BaseCommand):
    help = 'Import LC exam paper from PDF, extract questions and images'

    def add_arguments(self, parser):
        parser.add_argument('pdf_path', type=str, help='Path to the exam paper PDF')
        parser.add_argument('--year', type=int, required=True, help='Exam year (e.g., 2024)')
        parser.add_argument(
            '--paper',
            type=str,
            choices=['p1', 'p2'],
            required=True,
            help='Paper type (p1 or p2)'
        )
        parser.add_argument(
            '--start-page',
            type=int,
            default=1,
            help='Start page number (default: 1)'
        )
        parser.add_argument(
            '--end-page',
            type=int,
            help='End page number (optional, processes all pages if not specified)'
        )

    def handle(self, *args, **options):
        if not DEPENDENCIES_AVAILABLE:
            raise CommandError(
                'Missing dependencies. Install with:\n'
                'pip install PyPDF2 pdf2image Pillow poppler-utils'
            )

        pdf_path = options['pdf_path']
        exam_year = options['year']
        paper_type = options['paper']
        start_page = options['start_page']
        end_page = options['end_page']

        if not os.path.exists(pdf_path):
            raise CommandError(f'PDF file not found: {pdf_path}')

        self.stdout.write(self.style.SUCCESS(
            f'\nImporting {exam_year} Paper {paper_type.upper()} from: {pdf_path}\n'
        ))

        # Extract PDF content
        pdf_text = self._extract_text_from_pdf(pdf_path, start_page, end_page)

        # Extract images from PDF
        self.stdout.write('Extracting images from PDF...')
        images = self._extract_images_from_pdf(pdf_path, start_page, end_page)
        self.stdout.write(self.style.SUCCESS(f'Found {len(images)} images'))

        # Parse questions
        questions_data = self._parse_questions(pdf_text)
        self.stdout.write(self.style.SUCCESS(f'Parsed {len(questions_data)} questions\n'))

        # Get list of available topics
        topics = list(Topic.objects.all().order_by('name'))
        self.stdout.write('Available topics:')
        for idx, topic in enumerate(topics, 1):
            self.stdout.write(f'  {idx}. {topic.name}')
        self.stdout.write('')

        # Process each question interactively
        created_count = 0
        for q_num, q_data in enumerate(questions_data, 1):
            self.stdout.write(self.style.WARNING(f'\n--- Question {q_num} ---'))
            self.stdout.write(f"Text preview: {q_data['text'][:200]}...")
            self.stdout.write(f"Parts found: {', '.join([p['label'] for p in q_data['parts']])}")

            # Ask user to assign topic
            topic = self._select_topic(topics)

            # Skip if no topic selected
            if topic is None:
                self.stdout.write(self.style.WARNING('Skipped'))
                continue

            # Refresh topics list if a new one was created
            if topic not in topics:
                topics.append(topic)

            # Ask about images
            selected_images = self._assign_images(images, q_data)

            # Create the question
            question = self._create_question(
                topic=topic,
                order=q_num,
                year=exam_year,
                paper_type=paper_type,
                source_pdf=os.path.basename(pdf_path),
                images=selected_images,
                q_data=q_data
            )

            self.stdout.write(self.style.SUCCESS(f'Created: {question}'))
            created_count += 1

        self.stdout.write(self.style.SUCCESS(f'\n✅ Successfully imported {created_count} questions!'))

    def _extract_text_from_pdf(self, pdf_path, start_page, end_page):
        """Extract text from PDF"""
        text = ""
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            total_pages = len(pdf_reader.pages)

            if end_page is None:
                end_page = total_pages

            for page_num in range(start_page - 1, min(end_page, total_pages)):
                page = pdf_reader.pages[page_num]
                text += page.extract_text() + "\n"

        return text

    def _extract_images_from_pdf(self, pdf_path, start_page, end_page):
        """Extract images from PDF pages"""
        images = []
        try:
            pages = pdf2image.convert_from_path(
                pdf_path,
                first_page=start_page,
                last_page=end_page,
                dpi=200
            )
            for idx, page in enumerate(pages, start_page):
                images.append({
                    'page': idx,
                    'image': page,
                    'assigned': False
                })
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Could not extract images: {e}'))

        return images

    def _parse_questions(self, text):
        """Parse questions from extracted text"""
        questions = []

        # Pattern to match question numbers (e.g., "Question 1", "1.", etc.)
        # This is a simple pattern - you may need to adjust based on actual PDF format
        question_pattern = r'(?:Question\s+)?(\d+)\.?\s*\n'
        question_splits = re.split(question_pattern, text, flags=re.IGNORECASE)

        # Process pairs of (question_number, question_text)
        for i in range(1, len(question_splits), 2):
            if i + 1 < len(question_splits):
                q_num = question_splits[i]
                q_text = question_splits[i + 1].strip()

                # Parse parts (a), (b), (c), etc.
                parts = self._parse_question_parts(q_text)

                questions.append({
                    'number': int(q_num),
                    'text': q_text,
                    'parts': parts
                })

        return questions

    def _parse_question_parts(self, question_text):
        """Parse question parts like (a), (b), (c) from question text"""
        parts = []

        # Pattern to match (a), (b), (c), etc.
        part_pattern = r'\(([a-z])\)'
        part_splits = re.split(part_pattern, question_text)

        if len(part_splits) > 1:
            # Has multiple parts
            for i in range(1, len(part_splits), 2):
                if i + 1 < len(part_splits):
                    label = f"({part_splits[i]})"
                    text = part_splits[i + 1].strip()
                    parts.append({
                        'label': label,
                        'prompt': text
                    })
        else:
            # Single part question
            parts.append({
                'label': '',
                'prompt': question_text
            })

        return parts

    def _select_topic(self, topics):
        """Interactive topic selection"""
        while True:
            try:
                choice = input('Select topic number, "n" for new topic, or "s" to skip: ').strip()
                if choice.lower() == 's':
                    return None

                if choice.lower() == 'n':
                    # Create new topic
                    topic_name = input('Enter new topic name: ').strip()
                    if topic_name:
                        from django.utils.text import slugify
                        topic = Topic.objects.create(
                            name=topic_name,
                            slug=slugify(topic_name)
                        )
                        self.stdout.write(self.style.SUCCESS(f'Created new topic: {topic_name}'))
                        return topic
                    else:
                        self.stdout.write(self.style.ERROR('Topic name cannot be empty'))
                        continue

                idx = int(choice) - 1
                if 0 <= idx < len(topics):
                    return topics[idx]
                else:
                    self.stdout.write(self.style.ERROR('Invalid choice, try again'))
            except (ValueError, KeyboardInterrupt):
                self.stdout.write(self.style.ERROR('Invalid input'))

    def _assign_images(self, images, q_data):
        """Interactive image assignment"""
        if not images:
            return []

        self.stdout.write(f'\nFound {len(images)} total images in PDF')
        choice = input('Assign images to this question? (y/n): ').strip().lower()

        if choice != 'y':
            return []

        selected = []
        for img_data in images:
            if img_data['assigned']:
                continue

            self.stdout.write(f"  Image from page {img_data['page']}")
            assign = input('  Assign this image? (y/n/q to quit): ').strip().lower()

            if assign == 'q':
                break
            elif assign == 'y':
                img_data['assigned'] = True
                selected.append(img_data)

        return selected

    def _create_question(self, topic, order, year, paper_type, source_pdf, images, q_data):
        """Create Question and QuestionPart objects"""
        # Create main Question
        question = Question.objects.create(
            topic=topic,
            order=order,
            is_exam_question=True,
            exam_year=year,
            paper_type=paper_type,
            source_pdf_name=source_pdf,
            text=q_data['text'][:500] if len(q_data['text']) > 500 else q_data['text']
        )

        # Attach first image to question if available
        if images:
            img_pil = images[0]['image']
            img_bytes = io.BytesIO()
            img_pil.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            question.image.save(
                f'exam_{year}_{paper_type}_q{order}.png',
                ContentFile(img_bytes.read()),
                save=True
            )

        # Create QuestionParts
        for idx, part_data in enumerate(q_data['parts']):
            QuestionPart.objects.create(
                question=question,
                label=part_data['label'],
                prompt=part_data['prompt'],
                order=idx,
                expected_type='manual',  # Default to manual grading
                max_marks=0  # To be filled in later from marking scheme
            )

        return question