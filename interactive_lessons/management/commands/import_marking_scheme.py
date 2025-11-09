"""
Management command to import LC marking schemes and match to existing questions.
Usage: python manage.py import_marking_scheme <pdf_path> --year 2024 --paper p1
"""
import os
import re
from django.core.management.base import BaseCommand, CommandError
from interactive_lessons.models import Question, QuestionPart

try:
    import PyPDF2
    DEPENDENCIES_AVAILABLE = True
except ImportError:
    DEPENDENCIES_AVAILABLE = False


class Command(BaseCommand):
    help = 'Import LC marking scheme from PDF and match to existing exam questions'

    def add_arguments(self, parser):
        parser.add_argument('pdf_path', type=str, help='Path to the marking scheme PDF')
        parser.add_argument('--year', type=int, required=True, help='Exam year (e.g., 2024)')
        parser.add_argument(
            '--paper',
            type=str,
            choices=['p1', 'p2'],
            required=True,
            help='Paper type (p1 or p2)'
        )

    def handle(self, *args, **options):
        if not DEPENDENCIES_AVAILABLE:
            raise CommandError(
                'Missing dependencies. Install with:\n'
                'pip install PyPDF2'
            )

        pdf_path = options['pdf_path']
        exam_year = options['year']
        paper_type = options['paper']

        if not os.path.exists(pdf_path):
            raise CommandError(f'PDF file not found: {pdf_path}')

        self.stdout.write(self.style.SUCCESS(
            f'\nImporting marking scheme for {exam_year} Paper {paper_type.upper()}\n'
        ))

        # Find matching questions
        questions = Question.objects.filter(
            is_exam_question=True,
            exam_year=exam_year,
            paper_type=paper_type
        ).order_by('order')

        if not questions.exists():
            raise CommandError(
                f'No exam questions found for {exam_year} {paper_type}. '
                f'Import the exam paper first using import_exam_paper command.'
            )

        self.stdout.write(f'Found {questions.count()} questions to update')

        # Extract marking scheme text
        scheme_text = self._extract_text_from_pdf(pdf_path)

        # Parse marking scheme
        marking_data = self._parse_marking_scheme(scheme_text)

        # Match and update questions
        updated_count = 0
        for question in questions:
            q_num = question.order
            if q_num in marking_data:
                self.stdout.write(f'\nUpdating Question {q_num}...')
                self._update_question_with_scheme(question, marking_data[q_num])
                updated_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'\n✅ Successfully updated {updated_count} questions with marking schemes!'
        ))

    def _extract_text_from_pdf(self, pdf_path):
        """Extract text from PDF"""
        text = ""
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        return text

    def _parse_marking_scheme(self, text):
        """Parse marking scheme from extracted text"""
        marking_data = {}

        # Pattern to match question numbers
        question_pattern = r'(?:Question\s+)?(\d+)\.?\s*(?:\n|$)'
        question_splits = re.split(question_pattern, text, flags=re.IGNORECASE)

        # Process pairs of (question_number, marking_content)
        for i in range(1, len(question_splits), 2):
            if i + 1 < len(question_splits):
                q_num = int(question_splits[i])
                content = question_splits[i + 1].strip()

                # Parse parts and marks
                parts = self._parse_scheme_parts(content)

                marking_data[q_num] = {
                    'full_scheme': content,
                    'parts': parts
                }

        return marking_data

    def _parse_scheme_parts(self, scheme_text):
        """Parse individual parts (a), (b), (c) and extract marks"""
        parts = []

        # Pattern to match (a), (b), (c), etc.
        part_pattern = r'\(([a-z])\)'
        part_splits = re.split(part_pattern, scheme_text)

        if len(part_splits) > 1:
            # Has multiple parts
            for i in range(1, len(part_splits), 2):
                if i + 1 < len(part_splits):
                    label = f"({part_splits[i]})"
                    text = part_splits[i + 1].strip()

                    # Try to extract marks
                    marks = self._extract_marks(text)

                    # Try to extract answer
                    answer = self._extract_answer(text)

                    parts.append({
                        'label': label,
                        'scheme': text,
                        'marks': marks,
                        'answer': answer
                    })
        else:
            # Single part
            marks = self._extract_marks(scheme_text)
            answer = self._extract_answer(scheme_text)
            parts.append({
                'label': '',
                'scheme': scheme_text,
                'marks': marks,
                'answer': answer
            })

        return parts

    def _extract_marks(self, text):
        """Extract marks from text (e.g., '15 marks', '[15]', '(15m)')"""
        # Common patterns for marks
        patterns = [
            r'\[(\d+)\s*(?:marks?|m)?\]',  # [15 marks], [15m], [15]
            r'\((\d+)\s*(?:marks?|m)?\)',  # (15 marks), (15m), (15)
            r'(\d+)\s+marks?',              # 15 marks
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return int(match.group(1))

        return 0

    def _extract_answer(self, text):
        """Extract expected answer from marking scheme"""
        # Look for common answer patterns
        answer_patterns = [
            r'(?:Answer|Ans):\s*(.+?)(?:\n|$)',
            r'(?:Solution|Sol):\s*(.+?)(?:\n|$)',
            r'(?:Expected|Exp):\s*(.+?)(?:\n|$)',
        ]

        for pattern in answer_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        # If no explicit answer pattern, try to extract first significant line
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        if lines:
            # Skip lines that are just marks or labels
            for line in lines:
                if not re.match(r'^\[?\d+\]?\s*(?:marks?|m)?$', line, re.IGNORECASE):
                    return line

        return ""

    def _update_question_with_scheme(self, question, scheme_data):
        """Update question and its parts with marking scheme data"""
        # Update question solution
        question.solution = scheme_data['full_scheme']
        question.save()

        # Update question parts
        parts = question.parts.all().order_by('order')

        for idx, part in enumerate(parts):
            # Try to match by label
            matched_scheme = None
            for scheme_part in scheme_data['parts']:
                if scheme_part['label'] == part.label or (not scheme_part['label'] and idx == 0):
                    matched_scheme = scheme_part
                    break

            if matched_scheme:
                # Update part with marking scheme info
                if matched_scheme['answer']:
                    part.answer = matched_scheme['answer']
                if matched_scheme['marks']:
                    part.max_marks = matched_scheme['marks']
                part.solution = matched_scheme['scheme']
                part.save()

                self.stdout.write(
                    f"  {part.label or 'Part'}: {matched_scheme['marks']} marks"
                )
            else:
                self.stdout.write(self.style.WARNING(
                    f"  Could not match scheme for part {part.label}"
                ))