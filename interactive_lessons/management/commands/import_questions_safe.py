"""
Management command to import questions using natural keys.
This creates or updates sections/topics by name instead of ID.
"""
from django.core.management.base import BaseCommand
from interactive_lessons.models import Topic, Section, Question, QuestionPart
import json


class Command(BaseCommand):
    help = 'Import questions safely using natural keys to avoid ID conflicts'

    def add_arguments(self, parser):
        parser.add_argument(
            'filename',
            type=str,
            help='JSON file to import',
        )

    def handle(self, *args, **options):
        filename = options['filename']

        with open(filename, 'r') as f:
            data = json.load(f)

        questions_created = 0
        parts_created = 0
        question_map = {}  # Map local_id to new Question object

        for item in data:
            model = item['model']
            fields = item['fields']

            if model == 'interactive_lessons.question':
                # Get or create topic
                topic, _ = Topic.objects.get_or_create(name=fields['topic_name'])

                # Get or create section
                section = None
                if fields['section_name']:
                    section, _ = Section.objects.get_or_create(
                        topic=topic,
                        name=fields['section_name']
                    )

                # Create question
                question = Question.objects.create(
                    topic=topic,
                    section=section,
                    order=fields['order'],
                    hint=fields['hint'] or '',
                    solution=fields['solution'] or '',
                    solution_image=fields['solution_image'] or '',
                    is_exam_question=fields['is_exam_question'],
                    exam_year=fields.get('exam_year'),
                    paper_type=fields.get('paper_type'),
                    source_pdf_name=fields.get('source_pdf_name'),
                )

                # Map the local ID to new question
                question_map[fields['local_id']] = question
                questions_created += 1

                self.stdout.write(f"Created Question {question.id}: {topic.name}")

            elif model == 'interactive_lessons.questionpart':
                # Find the parent question
                local_question_id = fields['question_local_id']
                question = question_map.get(local_question_id)

                if not question:
                    self.stdout.write(self.style.WARNING(
                        f"⚠️  Skipping part - parent question not found (local_id={local_question_id})"
                    ))
                    continue

                # Create question part
                part = QuestionPart.objects.create(
                    question=question,
                    label=fields['label'],
                    prompt=fields['prompt'],
                    answer=fields['answer'] or '',
                    expected_format=fields.get('expected_format') or '',
                    hint=fields.get('hint') or '',
                    solution=fields.get('solution') or '',
                    solution_image=fields.get('solution_image') or '',
                    expected_type=fields['expected_type'],
                    max_marks=fields.get('max_marks', 0),
                    order=fields['order'],
                )

                parts_created += 1

        self.stdout.write(self.style.SUCCESS(
            f'\n✅ Import complete!'
        ))
        self.stdout.write(f'   Questions created: {questions_created}')
        self.stdout.write(f'   Parts created: {parts_created}')