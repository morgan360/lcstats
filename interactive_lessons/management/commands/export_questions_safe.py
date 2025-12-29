"""
Management command to export questions using natural keys instead of PKs.
This prevents ID conflicts between local and production databases.
"""
from django.core.management.base import BaseCommand
from django.core import serializers
from interactive_lessons.models import Question, QuestionPart
import json
from datetime import datetime


class Command(BaseCommand):
    help = 'Export questions safely using natural keys to avoid ID conflicts'

    def add_arguments(self, parser):
        parser.add_argument(
            '--ids',
            nargs='+',
            type=int,
            help='Specific question IDs to export',
        )
        parser.add_argument(
            '--section',
            type=str,
            help='Export all questions from a specific section name',
        )
        parser.add_argument(
            '--output',
            type=str,
            help='Output filename (default: questions_export_TIMESTAMP.json)',
        )

    def handle(self, *args, **options):
        if options['ids']:
            questions = Question.objects.filter(id__in=options['ids'])
        elif options['section']:
            questions = Question.objects.filter(section__name=options['section'])
        else:
            self.stdout.write(self.style.ERROR('Please specify --ids or --section'))
            return

        if not questions.exists():
            self.stdout.write(self.style.ERROR('No questions found!'))
            return

        # Get all question parts
        question_ids = list(questions.values_list('id', flat=True))
        parts = QuestionPart.objects.filter(question_id__in=question_ids)

        # Export data
        data = []

        for question in questions:
            q_data = {
                'model': 'interactive_lessons.question',
                'fields': {
                    'topic_name': question.topic.name,
                    'section_name': question.section.name if question.section else None,
                    'order': question.order,
                    'hint': question.hint,
                    'solution': question.solution,
                    'solution_image': str(question.solution_image) if question.solution_image else None,
                    'is_exam_question': question.is_exam_question,
                    'exam_year': question.exam_year,
                    'paper_type': question.paper_type,
                    'source_pdf_name': question.source_pdf_name,
                    'local_id': question.id,  # Store original ID for reference
                }
            }
            data.append(q_data)

            # Add parts for this question
            for part in parts.filter(question=question):
                p_data = {
                    'model': 'interactive_lessons.questionpart',
                    'fields': {
                        'question_local_id': question.id,  # Reference to parent question
                        'label': part.label,
                        'prompt': part.prompt,
                        'answer': part.answer,
                        'expected_format': part.expected_format,
                        'solution': part.solution,
                        'solution_image': str(part.solution_image) if part.solution_image else None,
                        'expected_type': part.expected_type,
                        'max_marks': part.max_marks,
                        'order': part.order,
                    }
                }
                data.append(p_data)

        # Write to file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = options['output'] or f'questions_safe_export_{timestamp}.json'

        with open(filename, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        self.stdout.write(self.style.SUCCESS(
            f'✅ Exported {questions.count()} questions to {filename}'
        ))
        self.stdout.write(f'   Total parts: {parts.count()}')