"""
Management command to read per-part mark allocations off the marking scheme,
preferring its text layer and falling back to the vision model.

Marks are the one piece of the marking scheme the database actually stores, so
that is all this extracts. Worked solutions stay as the scheme image itself -
see the note in exam_papers/models.py on why exam content is not held as text.

Two things learned the hard way, both now the default:

* The scheme prints a part's maximum as "Scale 10C (0, 3, 7, 10)", and where a
  part covers sub-parts its region holds one scale per sub-part. A vision read
  of the crop sees only the first, so a part worth 10 comes back worth 5 - and
  a low maximum quietly inflates every score against it. Reading the scales out
  of the text layer and summing them is exact, free and instant, so it is tried
  first; vision is the fallback for a scheme with no usable text.
* A question's total is known independently, from the paper itself, so parts
  that do not sum to it contain a misread. That check used to be opt-in and
  running without it put wrong marks on 27 of 70 questions in one sitting, so
  it is now on unless --no-verify-total says otherwise.
"""
from django.core.management.base import BaseCommand, CommandError

from exam_papers.models import ExamPaper
from exam_papers.services.vision_grading import extract_max_marks_from_scheme
from exam_papers.utils import (
    detect_marking_scheme_layout, parse_part_label, regions_for_letter,
    scale_marks_for_region,
)


class Command(BaseCommand):
    help = "Fill in question part max_marks from their marking scheme"

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
            help='Show what was read without saving to database'
        )
        parser.add_argument(
            '--overwrite',
            action='store_true',
            help='Also replace marks that are already set (default: fill blanks only)'
        )
        parser.add_argument(
            '--include-merged',
            action='store_true',
            help="Also read parts whose marking scheme spans several crops. "
                 "Only matters for the vision fallback, which reads the first "
                 "crop alone; the scheme text covers the whole region anyway"
        )
        parser.add_argument(
            '--verify-total',
            action='store_true',
            help='Deprecated: checking the total is now the default'
        )
        parser.add_argument(
            '--no-verify-total',
            action='store_false',
            dest='verify_total_enabled',
            help="Save what was read even when a question's parts do not sum "
                 "to its total. Only for a paper whose question totals are "
                 "themselves wrong - the marks will not be trustworthy"
        )
        parser.add_argument(
            '--no-vision',
            action='store_true',
            help='Read only the scheme text; never fall back to the vision model'
        )

    # ---- reading one question -------------------------------------------

    def _from_scheme_text(self, wanted, question, regions, scheme_path):
        """{part pk: marks} for every part whose scheme region states a scale."""
        proposal = {}
        for part in wanted:
            parsed = parse_part_label(part.label)
            if not parsed:
                continue
            # regions_for_letter gives the whole-letter region if the scheme
            # has one, and otherwise each of its sub-parts - never both, so
            # summing across what it returns cannot double-count.
            total, seen = 0, False
            for region in regions_for_letter(regions, question.question_number,
                                             parsed[0]):
                marks = scale_marks_for_region(scheme_path, region)
                if marks is not None:
                    total += marks
                    seen = True
            if seen:
                proposal[part.pk] = total
        return proposal

    def _from_vision(self, wanted):
        proposal = {}
        for part in wanted:
            if not part.solution_image:
                continue
            marks = extract_max_marks_from_scheme(part.solution_image, part.label)
            if marks is not None:
                proposal[part.pk] = marks
        return proposal

    def _adds_up(self, fixed, proposal, question, wanted):
        """True when every wanted part was read and they reach the total."""
        if len(proposal) != len(wanted):
            return False
        if not question.total_marks:
            return True
        return fixed + sum(proposal.values()) == question.total_marks

    def _read_question(self, question, options, counts, regions, scheme_path):
        """Read a whole question's marks, keeping them only if they add up.

        A question's total is known independently, from the paper itself, so it
        is a free check on whatever read the marks: parts that do not sum to it
        contain at least one misread, and writing them would put a wrong
        denominator under a student's grade.
        """
        overwrite = options['overwrite']
        include_merged = options['include_merged']
        verify = options['verify_total_enabled']

        parts = list(question.parts.all().order_by('order'))
        # A merged part covers several rows of the scheme. The scheme text
        # reads the whole region so it handles them, but the vision fallback
        # sees the first crop alone -- which would write, say, 10 onto a part
        # actually worth 25 and quietly halve every future score on it.
        merged = [p for p in parts
                  if not include_merged and p.extra_solution_images.exists()]
        wanted = [p for p in parts
                  if (overwrite or not p.max_marks) and p not in merged]
        if merged:
            self.stdout.write(self.style.WARNING(
                f'  {len(merged)} merged part(s) left to the scheme text only'))
        if not wanted:
            counts['skipped'] += len(parts)
            self.stdout.write('  nothing to read')
            return

        fixed = sum(p.max_marks or 0 for p in parts if p not in wanted)

        # The scheme's own text is exact wherever it is present, so it is worth
        # trying before paying for a vision read that sees less. A reading that
        # does not add up is kept aside rather than dropped: "read 45 against
        # 50" sends someone to the right page, where "nothing could be read"
        # sends them looking for a missing crop that is not the problem.
        proposal, source, rejected = {}, None, None
        if regions is not None:
            candidate = self._from_scheme_text(wanted, question, regions, scheme_path)
            if candidate and (not verify
                              or self._adds_up(fixed, candidate, question, wanted)):
                proposal, source = candidate, 'scheme text'
            elif candidate:
                rejected = candidate

        if not proposal and not options['no_vision']:
            for attempt in (1, 2):
                candidate = self._from_vision(wanted)
                if not verify or self._adds_up(fixed, candidate, question, wanted):
                    proposal, source = candidate, 'vision'
                    break
                rejected = candidate or rejected
                self.stdout.write(self.style.WARNING(
                    f'  parts sum to {fixed + sum(candidate.values())}, '
                    f'question is {question.total_marks}'
                    + ('  - re-reading' if attempt == 1 else '')
                ))

        if not proposal:
            if rejected:
                self.stdout.write(self.style.ERROR(
                    f'  still {fixed + sum(rejected.values())} against '
                    f'{question.total_marks} - left alone, needs entering by hand'
                ))
            else:
                self.stdout.write(self.style.ERROR('  nothing could be read'))
            counts['skipped'] += len(parts)
            return

        self.stdout.write(f'  read from the {source}')
        for part in wanted:
            if part.pk not in proposal:
                continue
            counts['read'] += 1
            self.stdout.write(self.style.SUCCESS(
                f'  {part.label}: {proposal[part.pk]} marks'
            ))
            if not options['dry_run']:
                part.max_marks = proposal[part.pk]
                part.save(update_fields=['max_marks'])
                counts['saved'] += 1
                counts['by_source'][source] = counts['by_source'].get(source, 0) + 1

    # ---- driving ---------------------------------------------------------

    def handle(self, *args, **options):
        try:
            paper = ExamPaper.objects.get(id=options['paper_id'])
        except ExamPaper.DoesNotExist:
            raise CommandError(f"ExamPaper with ID {options['paper_id']} not found")

        questions = paper.questions.all()
        if options.get('question'):
            questions = questions.filter(question_number=options['question'])

        self.stdout.write(self.style.SUCCESS(f'\n=== Reading marks for {paper} ==='))
        if options['dry_run']:
            self.stdout.write(self.style.WARNING('Dry run - nothing will be saved'))
        if not options['verify_total_enabled']:
            self.stdout.write(self.style.WARNING(
                'Total check disabled - the marks read will not be trustworthy'))

        # The scheme's text layer, read once for the whole paper.
        regions, scheme_path = None, None
        if paper.marking_scheme_pdf:
            scheme_path = paper.marking_scheme_pdf.path
            try:
                regions = detect_marking_scheme_layout(
                    scheme_path, 2 if paper.paper_type == 'p2' else 1)
            except Exception as error:          # a scheme that will not parse
                self.stdout.write(self.style.WARNING(
                    f'Could not read the scheme layout ({error}); '
                    f'falling back to the crops'))
        if not regions:
            self.stdout.write(self.style.WARNING(
                'No usable scheme text - reading the crops with vision'))

        counts = {'read': 0, 'saved': 0, 'skipped': 0, 'by_source': {}}
        for question in questions.order_by('order'):
            self.stdout.write(f'\n--- Question {question.question_number} ---')
            self._read_question(question, options, counts, regions, scheme_path)

        self.stdout.write(self.style.SUCCESS('\n=== Done ==='))
        self.stdout.write(
            f'Read: {counts["read"]}   Saved: {counts["saved"]}   '
            f'Skipped: {counts["skipped"]}'
        )
        if options['dry_run'] and counts['read']:
            self.stdout.write(
                self.style.WARNING('Re-run without --dry-run to save these marks.')
            )
        if counts['by_source'].get('vision'):
            self.stdout.write(
                'Vision misreads marks sometimes - check the parts read that '
                'way in admin before publishing.'
            )
