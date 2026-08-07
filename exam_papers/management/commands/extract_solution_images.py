"""
Management command to cut each question part's solution image out of the paper's
marking scheme PDF.

ExamQuestionPart.solution_image is what a student sees when they open a solution
and what the vision grader marks against, and it has to be attached by hand.
The scheme PDF already holds exactly that content, one row per part.

Matching is the risk, not cropping: part labels have been entered by hand in
many shapes - "(b), (i)", "(b),(i)", "b(ii)", "(b, (ii)" - so a label is parsed
down to a letter and an optional roman numeral before being looked up. Anything
that cannot be matched confidently is reported and left alone, because a
mis-attached crop shows a student the wrong solution and hands the grader the
wrong reference.
"""
import re

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError

from exam_papers.models import ExamPaper
from exam_papers.utils import (
    detect_marking_scheme_layout, render_marking_scheme_region, parse_part_label,
)

parse_label = parse_part_label


class Command(BaseCommand):
    help = "Cut per-part solution images out of a paper's marking scheme PDF"

    def add_arguments(self, parser):
        parser.add_argument('paper_id', type=int, help='ID of the ExamPaper')
        parser.add_argument(
            '--apply', action='store_true',
            help='Save the crops (default: report the matching and write nothing)'
        )
        parser.add_argument(
            '--overwrite', action='store_true',
            help='Replace solution images that are already set'
        )
        parser.add_argument(
            '--question', type=int,
            help='Limit to one question number'
        )

    def handle(self, *args, **options):
        apply_changes = options['apply']

        try:
            paper = ExamPaper.objects.get(id=options['paper_id'])
        except ExamPaper.DoesNotExist:
            raise CommandError(f"ExamPaper with ID {options['paper_id']} not found")
        if not paper.marking_scheme_pdf:
            raise CommandError(
                f'{paper} has no marking scheme PDF. Upload one in admin first.'
            )

        match = re.search(r'(\d)', paper.paper_type or '')
        if not match:
            raise CommandError(f'Cannot tell which paper {paper.paper_type!r} is')
        paper_number = int(match.group(1))

        pdf_path = paper.marking_scheme_pdf.path
        regions = detect_marking_scheme_layout(pdf_path, paper_number)
        if not regions:
            raise CommandError(
                f'Found no Paper {paper_number} section in the marking scheme. '
                'The scheme may not carry a usable text layer.'
            )

        self.stdout.write(self.style.SUCCESS(
            f'\n=== Solution images for {paper} ==='
        ))
        self.stdout.write(
            f'Marking scheme: {paper.marking_scheme_pdf.name.split("/")[-1]}  '
            f'({len(regions)} regions found for Paper {paper_number})'
        )
        if not apply_changes:
            self.stdout.write(self.style.WARNING('Report only - nothing will be saved\n'))

        saved = skipped = unmatched = unparsed = 0

        questions = paper.questions.all().order_by('question_number')
        if options.get('question'):
            questions = questions.filter(question_number=options['question'])

        for question in questions:
            for part in question.parts.all().order_by('order'):
                tag = f'Q{question.question_number} {part.label}'

                if part.solution_image and not options['overwrite']:
                    skipped += 1
                    continue

                parsed = parse_label(part.label)
                if not parsed:
                    self.stdout.write(self.style.ERROR(
                        f'  {tag:<22} label could not be read'
                    ))
                    unparsed += 1
                    continue

                letter, roman = parsed
                key = (question.question_number, letter, roman)
                region = regions.get(key)
                how = 'exact'

                # A part entered as "(b) (i)" when the scheme never split (b)
                # should still get the whole of (b).
                if region is None and roman:
                    region = regions.get((question.question_number, letter, None))
                    how = 'letter only'

                if region is None:
                    self.stdout.write(self.style.ERROR(
                        f'  {tag:<22} no region for ({letter})'
                        + (f'({roman})' if roman else '')
                    ))
                    unmatched += 1
                    continue

                pages = {s[0] + 1 for s in region['slices']}
                where = f"p{min(pages)}" + (f"-{max(pages)}" if len(pages) > 1 else '')
                self.stdout.write(
                    f'  {tag:<22} -> ({letter}){f"({roman})" if roman else ""} '
                    f'{where:<8} {how}'
                )

                if apply_changes:
                    data = render_marking_scheme_region(pdf_path, region)
                    name = (f'{paper.slug}_q{question.question_number}_'
                            f'{letter}{roman or ""}_ms.png')
                    part.solution_image.save(name, ContentFile(data), save=True)
                    saved += 1

        self.stdout.write(self.style.SUCCESS('\n=== Done ==='))
        self.stdout.write(
            f'Saved: {saved}   Already had an image: {skipped}   '
            f'No region: {unmatched}   Unreadable label: {unparsed}'
        )
        if not apply_changes:
            self.stdout.write(self.style.WARNING(
                'Re-run with --apply to save these crops.'
            ))
        else:
            self.stdout.write(
                'Spot-check a few in admin: a crop attached to the wrong part '
                'is worse than none at all.'
            )
