"""
Management command to propose a Topic for exam questions that have none, by
reading the question's text layer.

Topic is the one thing --auto cannot detect: it is a judgement about what a
question is about, not a fact printed on the paper. This narrows the manual job
to reviewing a proposal rather than reading every question cold.
"""
import json
import re
from pathlib import Path

from django.conf import settings
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

{examples}Rules:
- Many questions touch more than one topic. Pick the DOMINANT one - the topic
  carrying the most marks, not one that merely appears in passing.
- Where the examples above show how a topic is used, follow them. Several topic
  names are a filing convention rather than a piece of mathematics, and the
  examples are the only guide to which side of a split a question belongs on.
- A question set in an applied context keeps that context's topic even when the
  technique needed comes from elsewhere: a mortgage question that requires
  differentiation is still Finance.
- Inequalities are algebra. A question whose real work is solving or
  manipulating an inequality goes to an Algebra topic - use
  "Algebra-Inequalities and Factorisation" for inequalities and factorising,
  and "Algebra (1)" for other algebraic manipulation. Never file an inequality
  under Functions because it happens to mention f(x).
- Integration and differentiation are mixed together constantly. When a question
  uses both and neither plainly dominates, choose "Differential Calculus".
  Reserve "Integration" for questions that are substantially about integrating -
  areas under curves, definite integrals as the point of the exercise.
- Only pick "Random" if the question genuinely fits nothing else.
- Confidence: "high" only if the question is squarely one topic AND matches the
  examples for it. Use "medium" whenever you chose between two plausible topics,
  and "low" if the text is too sparse or garbled to tell. Most questions that
  span two topics deserve "medium" - do not default to "high".

The text below came out of a PDF, so the mathematical notation is mangled -
fractions collapse, radicals lose their extent. Read the prose for intent.

QUESTION {number}:
---
{text}
---

Respond with JSON only:
{{"topic": "<exact name from the list>", "confidence": "high|medium|low", "reason": "<at most 12 words>"}}"""

EXAMPLES_PATH = Path(settings.BASE_DIR) / 'exam_papers' / 'data' / 'topic_examples.json'


def load_examples(topics):
    """Render worked examples for the prompt, if build_topic_examples has run."""
    if not EXAMPLES_PATH.exists():
        return ''
    try:
        data = json.loads(EXAMPLES_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return ''

    names = {t.name for t in topics}
    blocks = []
    for name in sorted(data):
        if name not in names or not data[name]:
            continue
        shown = '\n'.join(f'  * {excerpt}' for excerpt in data[name])
        blocks.append(f'{name}:\n{shown}')

    if not blocks:
        return ''
    return (
        'Here is how questions already on file were classified. These show the '
        'filing conventions in use - match them.\n\n'
        + '\n\n'.join(blocks)
        + '\n\n'
    )


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

        examples = load_examples(topics)
        if examples:
            self.stdout.write(f'Using worked examples from {EXAMPLES_PATH.name}')
        else:
            self.stdout.write(self.style.WARNING(
                'No worked examples found - run build_topic_examples first for '
                'markedly better accuracy on the split topics'
            ))

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
                examples=examples,
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
