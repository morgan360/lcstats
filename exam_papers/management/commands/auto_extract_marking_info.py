"""
Management command to automatically extract marking information from marking scheme images using GPT-4 Vision.
This extracts: correct answers, mark allocations, solution steps, and common errors.
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from exam_papers.models import ExamPaper, ExamQuestion, ExamQuestionPart, MarkingScheme
import openai
import base64
import json
import os


class Command(BaseCommand):
    help = 'Automatically extract marking information from marking scheme PDF using GPT-4 Vision'

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
            help='Preview what would be extracted without saving to database'
        )

    def handle(self, *args, **options):
        paper_id = options['paper_id']
        question_filter = options.get('question')
        dry_run = options.get('dry_run', False)

        try:
            paper = ExamPaper.objects.get(id=paper_id)
        except ExamPaper.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'ExamPaper with ID {paper_id} not found'))
            return

        if not paper.marking_scheme_pdf:
            self.stdout.write(self.style.ERROR('No marking scheme PDF uploaded for this paper'))
            self.stdout.write('Please upload a marking scheme PDF in the admin first.')
            return

        # Set up OpenAI
        openai.api_key = settings.OPENAI_API_KEY
        if hasattr(settings, 'OPENAI_ORG_ID') and settings.OPENAI_ORG_ID:
            openai.organization = settings.OPENAI_ORG_ID

        self.stdout.write(self.style.SUCCESS(f'\n=== Auto-Extracting Marking Info for {paper} ==='))

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be saved'))

        # Get questions to process
        questions = paper.questions.all()
        if question_filter:
            questions = questions.filter(question_number=question_filter)

        for question in questions.order_by('order'):
            self.stdout.write(f'\n--- Processing Question {question.question_number} ---')

            # Check if question has an image
            if not question.image:
                self.stdout.write(self.style.WARNING(f'  No image for Q{question.question_number}, skipping'))
                continue

            # Process each part
            parts = question.parts.all().order_by('order')

            for part in parts:
                self.stdout.write(f'\nProcessing {part.label}...')

                # Encode the question image
                try:
                    with open(question.image.path, 'rb') as img_file:
                        image_data = base64.b64encode(img_file.read()).decode('utf-8')
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'  Error reading image: {str(e)}'))
                    continue

                # Create prompt for GPT-4 Vision
                prompt = f"""You are analyzing a Leaving Certificate Maths exam marking scheme.

Question Part: {part.label}
Question Text: {part.prompt if part.prompt else 'See image'}

Please extract the following information from this marking scheme:

1. **Correct Answer**: The final answer expected (as concise as possible)
2. **Max Marks**: Total marks for this part
3. **Marking Breakdown**: Steps with marks allocated to each
4. **Common Errors**: Common mistakes students make
5. **Solution Steps**: Brief solution working

Please respond in JSON format ONLY:
{{
  "answer": "the correct answer",
  "max_marks": 10,
  "steps": [
    {{"description": "Step 1 description", "marks": 2}},
    {{"description": "Step 2 description", "marks": 3}}
  ],
  "common_errors": [
    "Common error 1",
    "Common error 2"
  ],
  "solution": "Brief solution working/explanation",
  "partial_credit_notes": "Notes about partial credit"
}}

If you cannot determine something, use null for that field.
"""

                try:
                    # Call GPT-4 Vision API
                    response = openai.ChatCompletion.create(
                        model="gpt-4-vision-preview",
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": prompt},
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:image/jpeg;base64,{image_data}"
                                        }
                                    }
                                ]
                            }
                        ],
                        max_tokens=1000,
                        temperature=0.1
                    )

                    # Parse response
                    content = response.choices[0].message.content

                    # Extract JSON from response (handles markdown code blocks)
                    if '```json' in content:
                        json_str = content.split('```json')[1].split('```')[0].strip()
                    elif '```' in content:
                        json_str = content.split('```')[1].split('```')[0].strip()
                    else:
                        json_str = content.strip()

                    extracted_data = json.loads(json_str)

                    # Display what was extracted
                    self.stdout.write(self.style.SUCCESS(f'  ✓ Extracted data for {part.label}:'))
                    self.stdout.write(f'    Answer: {extracted_data.get("answer")}')
                    self.stdout.write(f'    Max Marks: {extracted_data.get("max_marks")}')
                    self.stdout.write(f'    Steps: {len(extracted_data.get("steps", []))} steps')
                    self.stdout.write(f'    Common Errors: {len(extracted_data.get("common_errors", []))} errors')

                    if not dry_run:
                        # Update the question part
                        if extracted_data.get('answer'):
                            part.answer = str(extracted_data['answer'])
                        if extracted_data.get('max_marks'):
                            part.max_marks = extracted_data['max_marks']
                        if extracted_data.get('solution'):
                            part.solution = extracted_data['solution']

                        part.save()

                        # Create or update marking scheme
                        marking_scheme, created = MarkingScheme.objects.get_or_create(
                            question_part=part
                        )

                        marking_breakdown = {
                            'steps': extracted_data.get('steps', []),
                            'common_errors': extracted_data.get('common_errors', []),
                            'partial_credit_notes': extracted_data.get('partial_credit_notes', '')
                        }

                        marking_scheme.marking_breakdown = marking_breakdown
                        marking_scheme.save()

                        self.stdout.write(self.style.SUCCESS(f'    ✓ Saved to database'))
                    else:
                        self.stdout.write(self.style.WARNING(f'    (Would save to database)'))

                except json.JSONDecodeError as e:
                    self.stdout.write(self.style.ERROR(f'  ✗ Failed to parse JSON: {str(e)}'))
                    self.stdout.write(f'  Raw response: {content}')
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'  ✗ Error: {str(e)}'))

        self.stdout.write(self.style.SUCCESS('\n=== Extraction Complete ==='))

        if dry_run:
            self.stdout.write(self.style.WARNING('\nThis was a dry run. To save results, run without --dry-run'))
        else:
            self.stdout.write('\nNext steps:')
            self.stdout.write('1. Review the extracted data in admin')
            self.stdout.write('2. Adjust any incorrect answers or marks')
            self.stdout.write('3. Publish the paper when ready')