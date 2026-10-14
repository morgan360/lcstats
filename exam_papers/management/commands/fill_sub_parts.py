"""
Management command to record which roman sub-parts each question part covers.

A part is a letter answered in one box, but on the paper (a) is often (i) and
(ii). Only the question image says so, and students answered (i) alone and lost
the marks for (ii). The marking scheme lists every sub-part under its letter,
so the scheme reader that cuts the solution images can name them too; the
question page then tells the student to answer all of them.

Report only unless --apply. Fills blanks only unless --overwrite, so a value
corrected by hand in admin is left alone.
"""
import re

from django.core.management.base import BaseCommand, CommandError

from exam_papers.models import ExamPaper
from exam_papers.utils import detect_marking_scheme_layout, parse_part_label

ROMAN_ORDER = ['i', 'ii', 'iii', 'iv', 'v', 'vi', 'vii', 'viii', 'ix', 'x']


class Command(BaseCommand):
    help = "Record each question part's roman sub-parts, read from the marking scheme"

    def add_arguments(self, parser):
        parser.add_argument('paper_id', type=int, nargs='?',
                            help='ID of one ExamPaper (default: every paper with a scheme)')
        parser.add_argument('--apply', action='store_true',
                            help='Save (default: report and write nothing)')
        parser.add_argument('--overwrite', action='store_true',
                            help='Replace sub-parts that are already set')

    def handle(self, *args, **options):
        papers = ExamPaper.objects.exclude(marking_scheme_pdf='').order_by('-year', 'paper_type')
        if options['paper_id']:
            papers = papers.filter(id=options['paper_id'])
            if not papers.exists():
                raise CommandError(f"ExamPaper {options['paper_id']} not found or has no scheme")
        if not options['apply']:
            self.stdout.write(self.style.WARNING('Report only - nothing will be saved'))

        changed = 0
        for paper in papers:
            match = re.search(r'(\d)', paper.paper_type or '')
            if not match:
                self.stdout.write(self.style.ERROR(f'{paper.slug}: cannot tell which paper'))
                continue
            regions = detect_marking_scheme_layout(paper.marking_scheme_pdf.path,
                                                   int(match.group(1)))
            if not regions:
                self.stdout.write(self.style.WARNING(f'{paper.slug}: scheme unreadable, skipped'))
                continue

            romans = {}
            for (number, letter, roman) in regions:
                if roman:
                    romans.setdefault((number, letter), set()).add(roman)

            for question in paper.questions.order_by('question_number'):
                for part in question.parts.order_by('order'):
                    parsed = parse_part_label(part.label)
                    if not parsed:
                        continue
                    found = romans.get((question.question_number, parsed[0]), set())
                    value = ','.join(r for r in ROMAN_ORDER if r in found)
                    if value == part.sub_parts:
                        continue
                    if part.sub_parts and not options['overwrite']:
                        continue
                    self.stdout.write(f'  {paper.slug} Q{question.question_number} '
                                      f'{part.label}: {part.sub_parts or "-"} -> {value or "-"}')
                    changed += 1
                    if options['apply']:
                        part.sub_parts = value
                        part.save(update_fields=['sub_parts'])

        verb = 'Saved' if options['apply'] else 'Would change'
        self.stdout.write(self.style.SUCCESS(f'{verb} {changed} part(s)'))
