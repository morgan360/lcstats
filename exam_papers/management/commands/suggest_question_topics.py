"""
Management command to propose a Topic for exam questions that have none, by
reading the question's text layer.

Topic is the one thing --auto cannot detect: it is a judgement about what a
question is about, not a fact printed on the paper. This narrows the manual job
to reviewing a proposal rather than reading every question cold.
"""
import json
import re

from django.core.management.base import BaseCommand, CommandError

from exam_papers.models import ExamPaper
from exam_papers.utils import (
    detect_question_layout, detect_legacy_question_layout, question_text,
)
from interactive_lessons.models import Topic
from notes.helpers.numskull import ask_openai


PROMPT = """You are classifying a Leaving Certificate Maths exam question by topic.

Choose exactly one topic from this list, copying the name character for character:

{topics}

Rules:
- Many questions touch more than one topic. Pick the DOMINANT one - the topic
  carrying the most marks, not one that merely appears in passing.
- Judge by what the student must actually DO, not by the objects mentioned. A
  question that differentiates the equation of a circle is calculus, not "The
  Circle".
- Only pick "Random" if the question genuinely fits nothing else.
- Confidence: "high" if the question is squarely one topic, "medium" if you had
  to choose between two reasonable topics, "low" if the text is too sparse or
  garbled to tell.

The text below came out of a PDF, so the mathematical notation is mangled -
fractions collapse, radicals lose their extent. Read the prose for intent.

QUESTION {number}:
---
{text}
---

Respond with JSON only:
{{"topic": "<exact name from the list>", "confidence": "high|medium|low", "reason": "<at most 12 words>"}}"""


class Command(BaseCommand):
    help = "Propose a Topic for exam questions that have none, from the PDF text"

    def add_arguments(self, parser):
        parser.add_argument('paper_id', type=int, help='ID of the ExamPaper')
        parser.add_argument(
            '--legacy',
            action='store_true',
            help='Paper predates 2012 Paper 2 and needs region detection'
        )
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Save the proposals (default: show them and write nothing)'
        )
        parser.add_argument(
            '--min-confidence',
            choices=['high', 'medium', 'low'],
            default='medium',
            help='Lowest confidence to save with --apply (default: medium)'
        )
        parser.add_argument(
            '--overwrite',
            action='store_true',
            help='Also reclassify questions that already have a topic'
        )

    def handle(self, *args, **options):
        apply_changes = options['apply']
        legacy = options['legacy']
        rank = {'high': 3, 'medium': 2, 'low': 1}
        floor = rank[options['min_confidence']]

        try:
            paper = ExamPaper.objects.get(id=options['paper_id'])
        except ExamPaper.DoesNotExist:
            raise CommandError(f"ExamPaper with ID {options['paper_id']} not found")
        if not paper.source_pdf:
            raise CommandError(f'{paper} has no source PDF')

        topics = list(Topic.objects.filter(subject=paper.subject).order_by('name'))
        if not topics:
            raise CommandError(f'No topics defined for {paper.subject}')
        by_name = {t.name.lower(): t for t in topics}

        pdf_path = paper.source_pdf.path
        layout = (detect_legacy_question_layout(pdf_path) if legacy
                  else detect_question_layout(pdf_path))
        if not layout:
            raise CommandError(
                'Could not detect question layout. Try --legacy for papers '
                'before 2012 Paper 2.'
            )
        detected = {item['question']: item for item in layout}

        self.stdout.write(self.style.SUCCESS(f'\n=== Topic proposals for {paper} ==='))
        if not apply_changes:
            self.stdout.write(self.style.WARNING('Proposal only - nothing will be saved\n'))

        saved = skipped = unmatched = 0

        for question in paper.questions.all().order_by('question_number'):
            if question.topic and not options['overwrite']:
                self.stdout.write(
                    f'  Q{question.question_number:<3} already {question.topic}, skipping'
                )
                skipped += 1
                continue

            item = detected.get(question.question_number)
            if not item:
                self.stdout.write(self.style.ERROR(
                    f'  Q{question.question_number:<3} not found in the PDF layout'
                ))
                continue

            text = question_text(pdf_path, item, legacy=legacy).strip()
            if len(text) < 40:
                self.stdout.write(self.style.ERROR(
                    f'  Q{question.question_number:<3} too little text to classify'
                ))
                continue

            prompt = PROMPT.format(
                topics='\n'.join(f'- {t.name}' for t in topics),
                number=question.question_number,
                text=text[:6000],
            )
            answer, error = ask_openai([{'role': 'user', 'content': prompt}])
            if error or not answer:
                self.stdout.write(self.style.ERROR(
                    f'  Q{question.question_number:<3} model call failed'
                ))
                continue

            match = re.search(r'\{.*\}', answer, re.DOTALL)
            try:
                result = json.loads(match.group(0) if match else answer)
            except (json.JSONDecodeError, AttributeError):
                self.stdout.write(self.style.ERROR(
                    f'  Q{question.question_number:<3} unparseable reply: {answer[:60]}'
                ))
                continue

            name = str(result.get('topic', '')).strip()
            confidence = str(result.get('confidence', 'low')).strip().lower()
            reason = str(result.get('reason', '')).strip()
            topic = by_name.get(name.lower())

            if not topic:
                self.stdout.write(self.style.ERROR(
                    f'  Q{question.question_number:<3} proposed "{name}", which is not a topic'
                ))
                unmatched += 1
                continue

            good = rank.get(confidence, 0) >= floor
            mark = ' ' if good else '~'
            line = (f'  {mark} Q{question.question_number:<3} {topic.name:<32} '
                    f'{confidence:<7} {reason}')
            self.stdout.write(self.style.SUCCESS(line) if good else line)

            if apply_changes and good:
                question.topic = topic
                question.save(update_fields=['topic'])
                saved += 1

        self.stdout.write(self.style.SUCCESS('\n=== Done ==='))
        self.stdout.write(f'Saved: {saved}   Already had a topic: {skipped}   '
                          f'Unrecognised topic name: {unmatched}')
        if not apply_changes:
            self.stdout.write(self.style.WARNING(
                'Re-run with --apply to save. Rows marked ~ are below the '
                'confidence floor and are left for you.'
            ))
        else:
            self.stdout.write('These are guesses - check them in admin before publishing.')
