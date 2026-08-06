"""
Management command to build worked examples for topic classification from the
questions already classified by hand.

Several topic names encode a convention rather than a piece of mathematics -
"Trigonometry (1)" against "(2)", "Algebra (1)" against "Algebra-Inequalities
and Factorisation" - and nothing in a question's text says which side of those
splits it belongs on. Showing the model how the existing questions were filed
teaches what no instruction can express.

Writes JSON to exam_papers/data/topic_examples.json, which
suggest_question_topics picks up automatically.
"""
import json
import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from exam_papers.models import ExamPaper, ExamQuestion
from exam_papers.utils import (
    detect_question_layout, detect_legacy_question_layout, question_text,
)

DEFAULT_PATH = Path(settings.BASE_DIR) / 'exam_papers' / 'data' / 'topic_examples.json'


def condense(text, limit):
    """Collapse extracted text to a single readable line of prose."""
    # Extraction leaves maths as scattered fragments on their own lines. Joining
    # and squeezing whitespace keeps the sentences, which is what carries topic.
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:limit]


class Command(BaseCommand):
    help = 'Build topic classification examples from already-classified questions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--per-topic', type=int, default=4,
            help='Maximum examples to keep per topic (default: 4)'
        )
        parser.add_argument(
            '--chars', type=int, default=260,
            help='Characters of each example to keep (default: 260)'
        )
        parser.add_argument(
            '--exclude', default='',
            help='Comma-separated paper ids to leave out, so they can be used '
                 'to measure accuracy without the answers leaking in'
        )
        parser.add_argument(
            '--output', default=str(DEFAULT_PATH),
            help=f'Where to write the JSON (default: {DEFAULT_PATH})'
        )

    def handle(self, *args, **options):
        per_topic = options['per_topic']
        chars = options['chars']
        excluded = {int(i) for i in options['exclude'].split(',') if i.strip()}

        questions = (ExamQuestion.objects
                     .exclude(topic=None)
                     .exclude(exam_paper_id__in=excluded)
                     .select_related('topic', 'exam_paper')
                     .order_by('exam_paper__year', 'question_number'))

        self.stdout.write(self.style.SUCCESS(
            f'\n=== Building examples from {questions.count()} classified questions ==='
        ))
        if excluded:
            self.stdout.write(f'Excluding papers: {sorted(excluded)}')

        layouts = {}
        by_topic = {}
        skipped = 0

        for question in questions:
            paper = question.exam_paper
            if not paper.source_pdf:
                skipped += 1
                continue

            if paper.id not in layouts:
                path = paper.source_pdf.path
                detected = detect_question_layout(path)
                legacy = False
                if not detected:
                    detected = detect_legacy_question_layout(path)
                    legacy = True
                layouts[paper.id] = ({i['question']: i for i in detected}, legacy, path)

            detected, legacy, path = layouts[paper.id]
            item = detected.get(question.question_number)
            if not item:
                skipped += 1
                continue

            bucket = by_topic.setdefault(question.topic.name, [])
            if len(bucket) >= per_topic:
                continue

            excerpt = condense(question_text(path, item, legacy=legacy), chars)
            if len(excerpt) < 60:
                skipped += 1
                continue
            bucket.append(excerpt)

        output = Path(options['output'])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(by_topic, indent=2, ensure_ascii=False))

        self.stdout.write('')
        for name in sorted(by_topic):
            self.stdout.write(f'  {name:<40} {len(by_topic[name])} examples')

        covered = len(by_topic)
        self.stdout.write(self.style.SUCCESS(
            f'\nWrote {output} - {covered} topics, {sum(len(v) for v in by_topic.values())} '
            f'examples, {skipped} questions skipped'
        ))
        self.stdout.write(
            'Topics with no examples fall back to their name alone, so they are '
            'the ones most likely to be misclassified.'
        )
