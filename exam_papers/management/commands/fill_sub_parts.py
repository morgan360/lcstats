"""
Management command to record which roman sub-parts each question part covers.

A part is a letter, but on the paper (a) is often (i) and (ii). The question
page gives such a part a box per sub-part; without them students answered (i)
alone and lost the marks for (ii). The question paper's text layer prints the
numerals under each letter, so they are read from there.

Not from the marking scheme: it repeats letter labels around its rows and files
numerals under the wrong letter -- 2025 Paper 1 Q7(b) came out as just "(ii)".

Only a clean run from (i) -- (i)(ii), (i)(ii)(iii)... -- is saved. Anything else
is reported and left alone: a box for a sub-part that does not exist, or none
for one that does, is worse than the single box.

Report only unless --apply. Fills blanks only unless --overwrite, so a value
corrected by hand in admin is left alone.
"""
from django.core.management.base import BaseCommand, CommandError

from exam_papers.models import ExamPaper
from exam_papers.utils import parse_part_label, question_sub_parts

ROMAN_ORDER = ['i', 'ii', 'iii', 'iv', 'v', 'vi', 'vii', 'viii', 'ix', 'x']


def clean_run(romans):
    return len(romans) >= 2 and romans == ROMAN_ORDER[:len(romans)]


class Command(BaseCommand):
    help = "Record each question part's roman sub-parts, read from the question paper"

    def add_arguments(self, parser):
        parser.add_argument('paper_id', type=int, nargs='?',
                            help='ID of one ExamPaper (default: every paper with a PDF)')
        parser.add_argument('--apply', action='store_true',
                            help='Save (default: report and write nothing)')
        parser.add_argument('--overwrite', action='store_true',
                            help='Replace sub-parts that are already set')

    def handle(self, *args, **options):
        papers = ExamPaper.objects.exclude(source_pdf='').order_by('-year', 'paper_type')
        if options['paper_id']:
            papers = papers.filter(id=options['paper_id'])
            if not papers.exists():
                raise CommandError(f"ExamPaper {options['paper_id']} not found or has no PDF")
        if not options['apply']:
            self.stdout.write(self.style.WARNING('Report only - nothing will be saved'))

        changed = doubtful = 0
        for paper in papers:
            found = question_sub_parts(paper.source_pdf.path)
            for question in paper.questions.order_by('question_number'):
                for part in question.parts.order_by('order'):
                    parsed = parse_part_label(part.label)
                    if not parsed:
                        continue
                    tag = f'{paper.slug} Q{question.question_number} {part.label}'
                    romans = found.get((question.question_number, parsed[0]), [])
                    if romans and not clean_run(romans):
                        self.stdout.write(self.style.WARNING(
                            f'  {tag}: read {",".join(romans)} - not a clean run, skipped'))
                        doubtful += 1
                        continue
                    value = ','.join(romans)
                    if value == part.sub_parts:
                        continue
                    if part.sub_parts and not options['overwrite']:
                        continue
                    self.stdout.write(f'  {tag}: {part.sub_parts or "-"} -> {value or "-"}')
                    changed += 1
                    if options['apply']:
                        part.sub_parts = value
                        part.save(update_fields=['sub_parts'])

        verb = 'Saved' if options['apply'] else 'Would change'
        self.stdout.write(self.style.SUCCESS(
            f'{verb} {changed} part(s); {doubtful} skipped as doubtful'))
