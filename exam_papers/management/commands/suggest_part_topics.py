"""
Management command to propose topics for each part of a paper's questions.

A question's single topic is its dominant one, but its parts often draw on
others - (a) Functions, (b) Differential Calculus - and a part is what a student
is sent to practise from a topic page. This proposes, per part, every topic the
part genuinely needs.

It never saves on the first pass. Proposals go to a JSON file for review; edit
the "topics" lists there if the model is wrong, then apply the reviewed file:

    python manage.py suggest_part_topics 12
    python manage.py suggest_part_topics --apply exam_papers/data/part_topics/2019-p1.json

The marking scheme is the best evidence of what a part is about - it shows the
working - so each part is given its scheme row's text alongside the question.
Parts without a scheme (2012-2015) are classified from the question alone and
say so in the file.
"""
import json
import os
import re
from datetime import date
from pathlib import Path

import fitz
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from exam_papers.management.commands.suggest_question_topics import load_examples
from exam_papers.models import ExamPaper, ExamQuestionPart
from exam_papers.utils import (
    detect_legacy_question_layout, detect_marking_scheme_layout,
    detect_question_layout, parse_part_label, question_text,
)
from interactive_lessons.models import Topic
from notes.helpers.numskull import ask_openai


OUTPUT_DIR = Path(settings.BASE_DIR) / 'exam_papers' / 'data' / 'part_topics'
RANK = {'high': 3, 'medium': 2, 'low': 1}

PROMPT = """You are filing the parts of a Leaving Certificate Maths exam question under topics.

Topics - copy names character for character:

{topics}

{examples}Rules:
- Give each part EVERY topic it genuinely needs, main topic first. Usually one
  or two; three only when a part really works across three.
- A secondary topic must carry real work in that part - a technique the student
  has to use. A word that merely appears, or a result carried over from an
  earlier part, does not count.
- Parts of one question often differ: (a) may be Functions while (c) is
  Integration. Judge each part on its own work, using the question text only
  for context.
- A part set in an applied context keeps that context's topic: a mortgage part
  that needs differentiation is Finance first, Differential Calculus second.
- Inequalities are algebra: "Algebra-Inequalities and Factorisation" for
  inequalities and factorising, "Algebra (1)" for other algebraic manipulation.
  Never file an inequality under Functions because it mentions f(x).
- Reserve "Integration" for parts substantially about integrating. Where
  differentiation and integration mix and neither dominates, lead with
  "Differential Calculus".
- Only use "Random" if a part fits nothing else.
- Confidence per part: "high" only if the topics are clear-cut; "medium" if you
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
{{"parts": [{{"id": <part id>, "topics": ["<main topic>", "..."], "confidence": "high|medium|low", "reason": "<at most 12 words>"}}]}}"""


def scheme_text(doc, region, limit=1500):
    """Text of one marking scheme region, across however many pages it spans."""
    chunks = []
    for page_index, y0, y1 in region['slices']:
        clip = fitz.Rect(0, y0, region['width'], y1)
        chunks.append(doc[page_index].get_text(clip=clip))
    return re.sub(r'\s+', ' ', ' '.join(chunks)).strip()[:limit]


def find_region(regions, question_number, label):
    """The scheme region for a part label, falling back from (b)(i) to (b)."""
    parsed = parse_part_label(label)
    if not parsed or not regions:
        return None
    letter, roman = parsed
    region = regions.get((question_number, letter, roman))
    if region is None and roman:
        region = regions.get((question_number, letter, None))
    return region


class Command(BaseCommand):
    help = 'Propose topics for each question part, or apply a reviewed proposal file'

    def add_arguments(self, parser):
        parser.add_argument('paper_id', type=int, nargs='?',
                            help='ID of the ExamPaper to propose topics for')
        parser.add_argument(
            '--apply', metavar='FILE',
            help='Save topics from a reviewed proposal file instead of proposing'
        )
        parser.add_argument(
            '--legacy', action='store_true',
            help='Paper predates 2012 Paper 2 and needs region detection'
        )
        parser.add_argument('--question', type=int, help='Limit to one question number')
        parser.add_argument(
            '--out', metavar='FILE',
            help='Where to write proposals (default: exam_papers/data/part_topics/<slug>.json)'
        )
        parser.add_argument(
            '--min-confidence', choices=['high', 'medium', 'low'], default='medium',
            help='With --apply, lowest confidence to save (default: medium)'
        )
        parser.add_argument(
            '--overwrite', action='store_true',
            help='With --apply, also replace topics already set by hand or a previous apply'
        )

    def handle(self, *args, **options):
        if options['apply']:
            self.apply_file(Path(options['apply']), options)
        elif options['paper_id']:
            self.propose(options)
        else:
            raise CommandError('Give a paper id to propose, or --apply FILE')

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

        questions = paper.questions.order_by('question_number').prefetch_related('parts__topics')
        if options['question']:
            questions = questions.filter(question_number=options['question'])

        self.stdout.write(self.style.SUCCESS(f'\n=== Part topic proposals for {paper} ==='))
        rows = []
        try:
            for question in questions:
                rows.extend(self.propose_question(
                    paper, question, topics, by_name, examples,
                    layout, regions, scheme_doc, options['legacy'],
                ))
        finally:
            if scheme_doc:
                scheme_doc.close()

        out = Path(options['out']) if options['out'] else OUTPUT_DIR / f'{paper.slug}.json'
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({
            'paper_id': paper.id,
            'paper': str(paper),
            'generated': date.today().isoformat(),
            'parts': rows,
        }, indent=2, ensure_ascii=False) + '\n')

        self.stdout.write(self.style.SUCCESS('\n=== Done ==='))
        self.stdout.write(f'Wrote {len(rows)} proposals to {out}')
        self.stdout.write(self.style.WARNING(
            'Nothing saved. Review and edit the "topics" lists, then run:\n'
            f'  python manage.py suggest_part_topics --apply {out}'
        ))

    def propose_question(self, paper, question, topics, by_name, examples,
                         layout, regions, scheme_doc, legacy):
        parts = list(question.parts.all())
        if not parts:
            return []
        tag = f'Q{question.question_number}'

        item = layout.get(question.question_number)
        text = ''
        if item:
            text = question_text(paper.source_pdf.path, item, legacy=legacy).strip()

        part_blocks, has_scheme = [], {}
        for part in parts:
            region = find_region(regions, question.question_number, part.label)
            body = scheme_text(scheme_doc, region) if region and scheme_doc else ''
            has_scheme[part.id] = bool(body)
            part_blocks.append(
                f'Part id {part.id}, label {part.label}, '
                f'{part.max_marks or "?"} marks\n'
                f'Marking scheme: {body or "(not available)"}'
            )

        if len(text) < 40 and not any(has_scheme.values()):
            self.stdout.write(self.style.ERROR(f'  {tag:<4} too little text to classify'))
            return []

        prompt = PROMPT.format(
            topics='\n'.join(f'- {t.name}' for t in topics),
            examples=examples,
            number=question.question_number,
            question_text=text[:5000] or '(not available)',
            parts='\n\n'.join(part_blocks),
        )
        answer, error = ask_openai([{'role': 'user', 'content': prompt}], temperature=0.2)
        if error or not answer:
            self.stdout.write(self.style.ERROR(f'  {tag:<4} model call failed'))
            return []

        match = re.search(r'\{.*\}', answer, re.DOTALL)
        try:
            result = json.loads(match.group(0) if match else answer)
            replies = {int(r['id']): r for r in result.get('parts', [])}
        except (json.JSONDecodeError, AttributeError, KeyError, TypeError, ValueError):
            self.stdout.write(self.style.ERROR(f'  {tag:<4} unparseable reply: {answer[:60]}'))
            return []

        rows = []
        for part in parts:
            reply = replies.get(part.id)
            if not reply:
                self.stdout.write(self.style.ERROR(f'  {tag} {part.label:<10} no proposal returned'))
                continue

            names, unknown = [], []
            for name in reply.get('topics') or []:
                topic = by_name.get(str(name).strip().lower())
                if topic and topic.name not in names:
                    names.append(topic.name)
                elif not topic:
                    unknown.append(str(name))
            confidence = str(reply.get('confidence', 'low')).strip().lower()
            reason = str(reply.get('reason', '')).strip()

            row = {
                'part_id': part.id,
                'question': question.question_number,
                'label': part.label,
                'topics': names,
                'confidence': confidence,
                'reason': reason,
                'current': [t.name for t in part.topics.all()],
                'from_scheme': has_scheme[part.id],
            }
            if unknown:
                row['unrecognised'] = unknown
            rows.append(row)

            line = (f'  {tag} {part.label:<10} {", ".join(names) or "-":<50} '
                    f'{confidence:<7} {reason}')
            if unknown:
                self.stdout.write(self.style.ERROR(f'{line}  [not topics: {", ".join(unknown)}]'))
            elif RANK.get(confidence, 0) >= RANK['medium']:
                self.stdout.write(self.style.SUCCESS(line))
            else:
                self.stdout.write(line)
        return rows

    # ------------------------------------------------------------------
    # Applying
    # ------------------------------------------------------------------
    def apply_file(self, path, options):
        if not path.exists():
            raise CommandError(f'{path} not found')
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            raise CommandError(f'{path} is not valid JSON: {exc}')

        try:
            paper = ExamPaper.objects.get(id=data['paper_id'])
        except (KeyError, ExamPaper.DoesNotExist):
            raise CommandError(f'{path} names no paper that exists')

        by_name = {t.name.lower(): t
                   for t in Topic.objects.filter(subject=paper.subject)}
        parts = {p.id: p for p in ExamQuestionPart.objects
                 .filter(question__exam_paper=paper)
                 .select_related('question').prefetch_related('topics')}
        floor = RANK[options['min_confidence']]

        self.stdout.write(self.style.SUCCESS(f'\n=== Applying part topics for {paper} ==='))
        saved = kept = low = invalid = 0

        for row in data.get('parts', []):
            part = parts.get(row.get('part_id'))
            tag = f"Q{row.get('question')} {row.get('label', '')}"
            if part is None:
                self.stdout.write(self.style.ERROR(f'  {tag:<16} not a part of {paper}'))
                invalid += 1
                continue

            topics, unknown = [], []
            for name in row.get('topics') or []:
                topic = by_name.get(str(name).strip().lower())
                (topics.append(topic) if topic else unknown.append(str(name)))
            if unknown or not topics:
                self.stdout.write(self.style.ERROR(
                    f'  {tag:<16} ' + (f'not topics: {", ".join(unknown)}'
                                       if unknown else 'no topics given')
                ))
                invalid += 1
                continue

            if RANK.get(str(row.get('confidence', '')).lower(), 0) < floor:
                self.stdout.write(f'  ~ {tag:<14} below confidence floor, left alone')
                low += 1
                continue

            # The migration seeded every part with its question's topic. Anything
            # else was set by hand or a previous apply, and is not overwritten
            # unless asked.
            current = {t.id for t in part.topics.all()}
            seeded = {part.question.topic_id} if part.question.topic_id else set()
            if current and current != seeded and not options['overwrite']:
                self.stdout.write(f'  = {tag:<14} already tagged, kept (use --overwrite)')
                kept += 1
                continue

            part.topics.set(topics)
            self.stdout.write(self.style.SUCCESS(
                f'  {tag:<16} {", ".join(t.name for t in topics)}'
            ))
            saved += 1

        self.stdout.write(self.style.SUCCESS('\n=== Done ==='))
        self.stdout.write(f'Saved: {saved}   Kept existing: {kept}   '
                          f'Below floor: {low}   Invalid: {invalid}')
