"""
Fold each part's stacked marking-scheme crops into its one solution image.

Parts used to go down to (a)(i), each with its own crop; merge_question_parts
folded them into their letter and stacked the crops behind the first as
ExamPartSolutionImage rows. A part's solution is one image now, so this joins
each stack into ExamQuestionPart.solution_image and deletes the rows.

By default the existing crops are stitched top to bottom, an exact repeat shown
once -- sub-parts printed in one table of the scheme were each given that table.
That keeps what is there, including any crop attached by hand. --recut cuts the
letter afresh from the paper's marking scheme PDF instead, which also cures a
crop that ran on into the next sub-part's rows; a part whose scheme gives no
region is stitched as usual and says so.

Report only unless --apply. The old files stay on disk, as they do when a row is
deleted anywhere else.
"""
import hashlib
import re

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from exam_papers.models import ExamQuestionPart
from exam_papers.utils import (
    detect_marking_scheme_layout, letter_region, parse_part_label,
    render_marking_scheme_region, stack_images,
)


class Command(BaseCommand):
    help = "Join each part's stacked marking-scheme crops into one image"

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true',
                            help='Save the joined images (default: report only)')
        parser.add_argument('--recut', action='store_true',
                            help='Cut each part afresh from the scheme PDF '
                                 'instead of stitching its crops')
        parser.add_argument('--paper', type=int, help='Limit to one ExamPaper id')

    def handle(self, *args, **options):
        apply_changes, recut = options['apply'], options['recut']
        parts = (ExamQuestionPart.objects
                 .filter(extra_solution_images__isnull=False).distinct()
                 .select_related('question__exam_paper')
                 .prefetch_related('extra_solution_images')
                 .order_by('question__exam_paper__year',
                           'question__exam_paper__paper_type',
                           'question__question_number', 'order'))
        if options.get('paper'):
            parts = parts.filter(question__exam_paper_id=options['paper'])

        if not apply_changes:
            self.stdout.write(self.style.WARNING('Report only - nothing will be saved\n'))

        layouts = {}
        joined = repeats = recuts = 0
        for part in parts:
            question = part.question
            paper = question.exam_paper
            crops = part.solution_images
            parsed = parse_part_label(part.label or '')
            letter = parsed[0] if parsed else 'x'
            tag = f'{paper} Q{question.question_number} {part.label}'

            region = None
            if recut:
                region = self._region(paper, question.question_number, letter,
                                      layouts)

            if region is not None:
                how = 'cut afresh from the scheme'
            else:
                hashes = [self._hash(crop) for crop in crops]
                dropped = len(hashes) - len(set(hashes))
                repeats += dropped
                how = f'{len(crops)} crops stitched' + (
                    f', {dropped} repeat{"s" if dropped > 1 else ""} dropped'
                    if dropped else '')
                if recut:
                    how += ' (no region in the scheme)'
            self.stdout.write(f'  {tag:<36} {how}')

            if not apply_changes:
                continue
            if region is not None:
                data = render_marking_scheme_region(
                    paper.marking_scheme_pdf.path, region)
                recuts += 1
            else:
                data = stack_images(crops)
            name = f'{paper.slug}_q{question.question_number}_{letter}_ms.png'
            part.solution_image.save(name, ContentFile(data), save=True)
            part.extra_solution_images.all().delete()
            joined += 1

        self.stdout.write(self.style.SUCCESS('\n=== Done ==='))
        self.stdout.write(f'Parts joined: {joined}   Cut afresh: {recuts}   '
                          f'Repeated crops dropped: {repeats}')
        if not apply_changes:
            self.stdout.write('Run with --apply to save.')

    def _region(self, paper, question_number, letter, layouts):
        """The letter's region in this paper's scheme, or None."""
        if paper.pk not in layouts:
            layouts[paper.pk] = None
            match = re.search(r'(\d)', paper.paper_type or '')
            if paper.marking_scheme_pdf and match:
                try:
                    layouts[paper.pk] = detect_marking_scheme_layout(
                        paper.marking_scheme_pdf.path, int(match.group(1)))
                except Exception as error:  # a missing or unreadable PDF
                    self.stdout.write(self.style.ERROR(
                        f'  {paper}: scheme could not be read ({error})'))
        return letter_region(layouts[paper.pk], question_number, letter)

    @staticmethod
    def _hash(file):
        file.open('rb')
        try:
            return hashlib.md5(file.read()).hexdigest()
        finally:
            file.close()
