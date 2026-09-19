"""File every part of a paper's questions under one topic, using the model.

A question's topic is its dominant one, but its parts often sit elsewhere --
(a) Functions, (b) Differential Calculus -- and a part is what a student is
sent to practise from a topic page. This gives each part the one topic
carrying most of its marks.

It writes as it goes. Proposals used to go to a JSON file for review, which
nobody ever reviewed; correcting a topic is now a dropdown on
/exam-papers/worksheet/parts/, which is a better place to do it than a text
editor. Use --dry-run to read the proposals first.

    python manage.py tag_part_topics 12 --dry-run
    python manage.py tag_part_topics 12

The marking scheme is the best evidence of what a part is about -- it shows the
working -- so each part is given its scheme rows' text alongside the question.
Parts without a scheme (2012-2015) are classified from the question alone.
"""
import json
import os
import re

import fitz
from django.core.management.base import BaseCommand, CommandError

from exam_papers.management.commands.suggest_question_topics import (
    algebra_rule, load_examples,
)
from exam_papers.models import ExamPaper, ExamQuestionPart
from exam_papers.utils import (
    detect_legacy_question_layout, detect_marking_scheme_layout,
    detect_question_layout, parse_part_label, question_text, regions_for_letter,
)
from interactive_lessons.models import Topic
from notes.helpers.numskull import ask_openai


RANK = {'high': 3, 'medium': 2, 'low': 1}

PROMPT = """You are filing the parts of a Leaving Certificate Maths exam question under topics.

Topics - copy names character for character:

{topics}

{examples}Rules:
- Choose exactly ONE topic for each part: the one carrying most of that part's
  marks. Not the topic it touches in passing, and not the question's overall
  subject - the one the marks are for.
- Parts of one question often differ: (a) may be Functions while (c) is
  Integration. Judge each part on its own work, using the question text only
  for context.
- A part set in an applied context keeps that context's topic: a mortgage part
  that needs differentiation is Finance first, Differential Calculus second.
{algebra_rule}- Reserve "Integration" for parts substantially about integrating. Where
  differentiation and integration mix and neither dominates, lead with
  "Differential Calculus".
- Only use "Random" if a part fits nothing else.
- Confidence per part: "high" only if the topic is clear-cut; "medium" if you
  weighed a plausible alternative; "low" if the text is too sparse or garbled.

The text came out of PDFs, so the notation is mangled - fractions collapse,
radicals lose their extent. Read the prose and the shape of the working.

QUESTION {number} (whole question, for context):
---
{question_text}
---

PARTS:
{parts}

Respond with JSON only, one entry per part id above:
{{"parts": [{{"id": <part id>, "topic": "<exact topic name>", "confidence": "high|medium|low", "reason": "<at most 12 words>"}}]}}"""


def scheme_text(doc, region, limit=1500):
    """Text of one marking scheme region, across however many pages it spans."""
    chunks = []
    for page_index, y0, y1 in region['slices']:
        clip = fitz.Rect(0, y0, region['width'], y1)
        chunks.append(doc[page_index].get_text(clip=clip))
    return re.sub(r'\s+', ' ', ' '.join(chunks)).strip()[:limit]


def part_scheme_text(doc, regions, question_number, label):
    """The scheme text for a part, across every region its letter covers.

    A part is a whole letter now. Where the scheme still splits (b) into
    (b)(i) and (b)(ii) there is no (b) region, so the sub-regions are read and
    joined -- otherwise a merged part would be classified from nothing.
    """
    parsed = parse_part_label(label)
    if not parsed or not regions or not doc:
        return ''
    found = regions_for_letter(regions, question_number, parsed[0])
    return ' '.join(scheme_text(doc, region) for region in found).strip()[:1500]


class Command(BaseCommand):
    help = 'Give every part of a paper one topic, using the model'

    def add_arguments(self, parser):
        parser.add_argument('paper_id', type=int,
                            help='ID of the ExamPaper to tag')
        parser.add_argument(
            '--legacy', action='store_true',
            help='Paper predates 2012 Paper 2 and needs region detection'
        )
        parser.add_argument('--question', type=int, help='Limit to one question number')
        parser.add_argument('--dry-run', action='store_true',
                            help='Print what would be set, and write nothing')

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.counts = {'set': 0, 'unchanged': 0, 'unrecognised': 0, 'no reply': 0}
        self.low_confidence = []
        self.propose(options)

    # ------------------------------------------------------------------
    # Proposing
    # ------------------------------------------------------------------
    def propose(self, options):
        try:
            paper = ExamPaper.objects.get(id=options['paper_id'])
        except ExamPaper.DoesNotExist:
            raise CommandError(f"ExamPaper with ID {options['paper_id']} not found")

        topics = list(Topic.objects.filter(subject=paper.subject).order_by('name'))
        if not topics:
            raise CommandError(f'No topics defined for {paper.subject}')
        by_name = {t.name.lower(): t for t in topics}
        examples = load_examples(topics)
        if not examples:
            self.stdout.write(self.style.WARNING(
                'No worked examples found - run build_topic_examples first for '
                'markedly better accuracy on the split topics'
            ))

        layout = {}
        if paper.source_pdf and os.path.exists(paper.source_pdf.path):
            detected = (detect_legacy_question_layout(paper.source_pdf.path)
                        if options['legacy']
                        else detect_question_layout(paper.source_pdf.path))
            layout = {item['question']: item for item in detected}
        if not layout:
            self.stdout.write(self.style.WARNING(
                'No question layout from the paper PDF - classifying from the '
                'marking scheme alone'
            ))

        regions, scheme_doc = {}, None
        match = re.search(r'(\d)', paper.paper_type or '')
        if (paper.marking_scheme_pdf and match
                and os.path.exists(paper.marking_scheme_pdf.path)):
            regions = detect_marking_scheme_layout(
                paper.marking_scheme_pdf.path, int(match.group(1))) or {}
            if regions:
                scheme_doc = fitz.open(paper.marking_scheme_pdf.path)
        if not regions:
            self.stdout.write(self.style.WARNING(
                'No marking scheme regions - classifying from the question text alone'
            ))

        questions = (paper.questions.order_by('question_number')
                     .prefetch_related('parts__topic'))
        if options['question']:
            questions = questions.filter(question_number=options['question'])

        heading = ('Part topics that would be set' if self.dry_run
                   else 'Setting part topics')
        self.stdout.write(self.style.SUCCESS(f'\n=== {heading} for {paper} ==='))
        try:
            for question in questions:
                self.tag_question(
                    paper, question, topics, by_name, examples,
                    layout, regions, scheme_doc, options['legacy'],
                )
        finally:
            if scheme_doc:
                scheme_doc.close()

        self.stdout.write(self.style.SUCCESS('\n=== Done ==='))
        verb = 'Would set' if self.dry_run else 'Set'
        self.stdout.write(
            f"{verb}: {self.counts['set']}   "
            f"Unchanged: {self.counts['unchanged']}   "
            f"Unrecognised: {self.counts['unrecognised']}   "
            f"No reply: {self.counts['no reply']}")
        if self.low_confidence:
            self.stdout.write(self.style.WARNING(
                'Worth a look on /exam-papers/worksheet/parts/ - the model was '
                'unsure about: ' + ', '.join(self.low_confidence)))
        if self.dry_run:
            self.stdout.write(self.style.WARNING(
                'Nothing was written. Re-run without --dry-run.'))

    def tag_question(self, paper, question, topics, by_name, examples,
                     layout, regions, scheme_doc, legacy):
        parts = list(question.parts.all())
        if not parts:
            return
        tag = f'Q{question.question_number}'

        item = layout.get(question.question_number)
        text = ''
        if item:
            text = question_text(paper.source_pdf.path, item, legacy=legacy).strip()

        part_blocks, has_scheme = [], {}
        for part in parts:
            body = part_scheme_text(scheme_doc, regions,
                                    question.question_number, part.label)
            has_scheme[part.id] = bool(body)
            part_blocks.append(
                f'Part id {part.id}, label {part.label}, '
                f'{part.max_marks or "?"} marks\n'
                f'Marking scheme: {body or "(not available)"}'
            )

        if len(text) < 40 and not any(has_scheme.values()):
            self.stdout.write(self.style.ERROR(f'  {tag:<4} too little text to classify'))
            self.counts['no reply'] += len(parts)
            return

        prompt = PROMPT.format(
            topics='\n'.join(f'- {t.name}' for t in topics),
            examples=examples,
            algebra_rule=algebra_rule(topics, subject='part'),
            number=question.question_number,
            question_text=text[:5000] or '(not available)',
            parts='\n\n'.join(part_blocks),
        )
        answer, error = ask_openai([{'role': 'user', 'content': prompt}], temperature=0.2)
        if error or not answer:
            self.stdout.write(self.style.ERROR(f'  {tag:<4} model call failed'))
            self.counts['no reply'] += len(parts)
            return

        match = re.search(r'\{.*\}', answer, re.DOTALL)
        try:
            result = json.loads(match.group(0) if match else answer)
            replies = {int(r['id']): r for r in result.get('parts', [])}
        except (json.JSONDecodeError, AttributeError, KeyError, TypeError, ValueError):
            self.stdout.write(self.style.ERROR(f'  {tag:<4} unparseable reply: {answer[:60]}'))
            self.counts['no reply'] += len(parts)
            return

        for part in parts:
            self.tag_part(tag, part, replies.get(part.id), by_name)

    def tag_part(self, tag, part, reply, by_name):
        """Set one part's topic from the model's reply, or explain why not."""
        label = f'{tag} {part.label}'
        was = part.topic.name if part.topic else '-'

        if not reply:
            self.stdout.write(self.style.ERROR(f'  {label:<14} no reply for this part'))
            self.counts['no reply'] += 1
            return

        # Models return a list even when asked for one name; take the first.
        raw = reply.get('topic')
        if isinstance(raw, (list, tuple)):
            raw = raw[0] if raw else None

        # Exact match only. A near-match landing on the wrong side of the
        # Algebra split is worse than leaving the part where it is.
        topic = by_name.get(str(raw).strip().lower()) if raw else None
        if topic is None:
            self.stdout.write(self.style.ERROR(
                f'  {label:<14} left as {was}  [not a topic: {raw!r}]'))
            self.counts['unrecognised'] += 1
            return

        confidence = str(reply.get('confidence', 'low')).strip().lower()
        reason = str(reply.get('reason', '')).strip()
        if RANK.get(confidence, 0) < RANK['medium']:
            self.low_confidence.append(label)

        if part.topic_id == topic.id:
            self.stdout.write(f'  = {label:<12} {topic.name}')
            self.counts['unchanged'] += 1
            return

        line = (f'  {label:<14} {topic.name:<28} {confidence:<7} {reason}'
                f'  [was: {was}]')
        if not self.dry_run:
            part.topic = topic
            part.save(update_fields=['topic'])
        self.stdout.write(self.style.SUCCESS(line) if confidence == 'high' else line)
        self.counts['set'] += 1
