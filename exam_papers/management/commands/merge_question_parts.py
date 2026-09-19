"""Fold (b)(i) and (b)(ii) into a single (b), and tidy the labels while there.

Parts were tagged and set as homework down to sub-part level. One level is as
far as anyone can keep correct by hand, so a part is now a letter: (a), (b),
(c). A question's sub-parts of the same letter become one part carrying all of
their marking-scheme crops and the sum of their marks.

It writes only with --apply. Every foreign key pointing at a part -- student
attempts, homework tasks, photographed working -- is ON DELETE CASCADE, so an
error between deleting a row and repointing what referenced it destroys work a
student did. The inert run is the one you get if you fumble the invocation.

    manage.py merge_question_parts                    # say what would happen
    manage.py merge_question_parts --apply            # do it
    manage.py merge_question_parts --paper 3 --apply  # one paper at a time
    manage.py merge_question_parts --check            # exit 1 if any remain
"""
import re
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction

from exam_papers.models import (
    ExamPartSolutionImage, ExamQuestionAttempt, ExamQuestionPart,
)
from exam_papers.utils import parse_part_label


ROMAN_RANK = {None: 0, 'i': 1, 'ii': 2, 'iii': 3, 'iv': 4,
              'v': 5, 'vi': 6, 'vii': 7, 'viii': 8}

# parse_part_label looks for [a-h] with no word boundary, so "Part (b)" parses
# as letter "a" -- the a of "Part". Labels are only 10 characters, but that is
# room enough for someone to have typed it. Rather than change a function the
# classifier and extract_solution_images also depend on, refuse anything whose
# letter is flanked by other letters and say so in the report.
_FLANKED = re.compile(r'[a-z][a-h]|[a-h][a-z]', re.I)

# A part can be one letter's worth of work or several sub-steps of one letter,
# but "(a), (b)" is one part covering two letters, with no (b) of its own in
# the question. Calling that (a) would tell a student to answer half of what
# its marking scheme covers, so it is left exactly as typed and reported.
_TWO_LETTERS = re.compile(r'\(\s*([a-h])\s*\).*?\(\s*([a-h])\s*\)', re.I)


class Command(BaseCommand):
    help = "Merge a question's sub-parts into one part per letter."

    def add_arguments(self, parser):
        parser.add_argument('--paper', type=int,
                            help='Only parts of this exam paper id.')
        parser.add_argument('--question', type=int,
                            help='Only this question number, within --paper.')
        parser.add_argument('--apply', action='store_true',
                            help='Actually write. Without it, nothing changes.')
        parser.add_argument('--dry-run', action='store_true',
                            help='Explicitly do nothing (the default anyway).')
        parser.add_argument(
            '--sum-partial-marks', action='store_true',
            help="Sum the marks even when a sub-part's are blank, instead of "
                 "leaving the merged part's marks blank for checking.")
        parser.add_argument(
            '--dedupe-tasks', action='store_true',
            help='Remove homework tasks left pointing twice at one part. '
                 'Never removes one a student has progress against.')
        parser.add_argument('--check', action='store_true',
                            help='Print how many groups are unmerged and exit '
                                 '1 if any are. Implies no writing.')

    def handle(self, *args, **options):
        self.apply = options['apply'] and not options['check']
        self.sum_partial = options['sum_partial_marks']
        self.dedupe = options['dedupe_tasks']

        parts = self._scope(options)
        groups, unreadable = self._group(parts)

        if options['check']:
            pending = [g for g in groups.values() if self._needs_work(g)]
            self.stdout.write(f'{len(pending)} group(s) still to merge.')
            if pending:
                raise SystemExit(1)
            return

        self._report_labels(parts)

        totals = defaultdict(int)
        for (question, letter), members in sorted(
                groups.items(), key=lambda kv: (kv[0][0].pk, kv[0][1])):
            if not self._needs_work(members):
                continue
            self._handle_group(question, letter, members, totals)

        self._report_unreadable(unreadable)
        self._report_marks_to_check(totals)
        self._summarise(totals, groups)

    # ---- gathering ------------------------------------------------------

    def _scope(self, options):
        parts = (ExamQuestionPart.objects
                 .select_related('question__exam_paper', 'topic')
                 .prefetch_related('extra_solution_images'))
        if options['paper']:
            parts = parts.filter(question__exam_paper_id=options['paper'])
        if options['question']:
            parts = parts.filter(question__question_number=options['question'])
        # order and id together, because order defaults to 0 and plenty of rows
        # have never been given one.
        return list(parts.order_by('question_id', 'order', 'id'))

    def _group(self, parts):
        groups, unreadable = defaultdict(list), []
        for part in parts:
            letter = self._letter(part)
            if letter is None:
                unreadable.append(part)
                continue
            groups[(part.question, letter)].append(part)
        for members in groups.values():
            members.sort(key=self._rank)
        return groups, unreadable

    def _letter(self, part):
        label = (part.label or '').strip()
        if _FLANKED.search(label):
            return None
        match = _TWO_LETTERS.search(label)
        if match and match.group(1).lower() != match.group(2).lower():
            return None
        parsed = parse_part_label(label)
        return parsed[0] if parsed else None

    def _rank(self, part):
        parsed = parse_part_label(part.label or '')
        roman = parsed[1] if parsed else None
        return (ROMAN_RANK.get(roman, 99), part.order or 0, part.pk)

    def _needs_work(self, members):
        """A group is done when it is one part already wearing its letter."""
        if len(members) > 1:
            return True
        parsed = parse_part_label(members[0].label or '')
        return members[0].label != f'({parsed[0]})'

    # ---- doing it -------------------------------------------------------

    def _handle_group(self, question, letter, members, totals):
        survivor, losers = members[0], members[1:]
        canonical = f'({letter})'
        where = f'{question.exam_paper} Q{question.question_number} {canonical}'

        marks, marks_note = self._marks(members)
        crops = self._crops(members)
        moving = self._referencing(losers)

        self.stdout.write(self.style.MIGRATE_HEADING(where))
        self.stdout.write(
            f'  {" + ".join(repr(p.label) for p in members)} '
            f'-> {canonical} (keeping part {survivor.pk})')
        self.stdout.write(f'  marks: {marks_note}')
        if len(crops) > 1:
            self.stdout.write(f'  {len(crops)} marking-scheme crops stacked')
        if any(moving.values()):
            self.stdout.write(
                '  moving: '
                + ', '.join(f'{n} {name}' for name, n in moving.items() if n))

        totals['groups'] += 1
        totals['deleted'] += len(losers)
        totals['crops'] += max(0, len(crops) - 1)
        for name, count in moving.items():
            totals[name] += count
        if marks is None and any(p.max_marks for p in members):
            totals.setdefault('marks_to_check', [])

        if not self.apply:
            return

        with transaction.atomic():
            # Repoint everything before anything is deleted: these FKs cascade.
            ExamQuestionAttempt.objects.filter(
                question_part__in=losers).update(question_part=survivor)
            self._repoint_work_submissions(losers, survivor)
            self._repoint_homework_tasks(losers, survivor)

            self._stack_crops(survivor, crops)

            # Delete first, save the label second. The group is by construction
            # every part of this question with this letter, so once the losers
            # are gone nothing else can be holding (x) and the unique_together
            # on (question, label) is never in danger.
            for loser in losers:
                loser.delete()

            survivor.label = canonical
            survivor.max_marks = marks
            survivor.order = min(p.order or 0 for p in members)
            survivor.topic = next(
                (p.topic for p in members if p.topic_id), None) or question.topic
            survivor.solution_unlock_after_attempts = min(
                p.solution_unlock_after_attempts for p in members)
            survivor.save()

    def _marks(self, members):
        """(value, explanation). Blank unless every member had marks."""
        values = [p.max_marks for p in members]
        shown = ' + '.join(str(v) if v is not None else 'blank' for v in values)
        known = [v for v in values if v is not None]

        if all(v is not None for v in values):
            total = sum(known) if len(values) > 1 else values[0]
            return total, f'{shown} = {total}'
        if self.sum_partial:
            total = sum(known) or None
            return total, f'{shown} = {total} (--sum-partial-marks)'
        # An understated maximum quietly inflates every future score on this
        # part; a blank one shows as "? marks" and gets noticed.
        return None, f'{shown} -> blank, needs checking'

    def _crops(self, members):
        """Every marking-scheme image in the group, in reading order."""
        return [image for part in members for image in part.solution_images]

    def _stack_crops(self, survivor, crops):
        """Primary stays put; the rest become extra_solution_images.

        The files are handed over by name. Re-saving the bytes would duplicate
        them, and deleting a row does not delete its file, so this is a change
        of owner and nothing on disk moves.
        """
        if not crops:
            return
        primary, extras = crops[0], crops[1:]
        if survivor.solution_image.name != primary.name:
            survivor.solution_image.name = primary.name

        survivor.extra_solution_images.all().delete()
        ExamPartSolutionImage.objects.bulk_create([
            ExamPartSolutionImage(part=survivor, order=index)
            for index, _ in enumerate(extras)
        ])
        for row, image in zip(survivor.extra_solution_images.order_by('order'),
                              extras):
            row.image.name = image.name
            row.save(update_fields=['image'])

    # ---- the things that point at a part --------------------------------

    def _referencing(self, losers):
        from homework.models import HomeworkTask
        from students.models import WorkSubmission

        if not losers:
            return {'attempts': 0, 'homework tasks': 0, 'work photos': 0}
        return {
            'attempts': ExamQuestionAttempt.objects.filter(
                question_part__in=losers).count(),
            'homework tasks': HomeworkTask.objects.filter(
                exam_question_part__in=losers).count(),
            'work photos': WorkSubmission.objects.filter(
                exam_question_part__in=losers).count(),
        }

    def _repoint_work_submissions(self, losers, survivor):
        from students.models import WorkSubmission
        WorkSubmission.objects.filter(
            exam_question_part__in=losers).update(exam_question_part=survivor)

    def _repoint_homework_tasks(self, losers, survivor):
        """Move tasks to the survivor, and mind the duplicates that makes.

        Two tasks in one assignment can end up on the same part. They are
        reported rather than removed, because StudentHomeworkProgress cascades
        off a task and deleting one throws away a student's completion.
        """
        from homework.models import HomeworkTask, StudentHomeworkProgress

        HomeworkTask.objects.filter(
            exam_question_part__in=losers).update(exam_question_part=survivor)

        seen = set()
        for task in HomeworkTask.objects.filter(
                exam_question_part=survivor).order_by('assignment_id', 'order', 'pk'):
            key = (task.assignment_id, task.exam_question_part_id)
            if key not in seen:
                seen.add(key)
                continue
            has_progress = StudentHomeworkProgress.objects.filter(
                assignment_id=task.assignment_id).exists()
            if self.dedupe and not has_progress:
                self.stdout.write(f'  removed duplicate homework task {task.pk}')
                task.delete()
            else:
                self.stdout.write(self.style.WARNING(
                    f'  duplicate homework task {task.pk} on assignment '
                    f'{task.assignment_id}'
                    + (' (kept: a student has progress on it)' if has_progress
                       else ' (use --dedupe-tasks)')))

    # ---- reporting ------------------------------------------------------

    def _report_labels(self, parts):
        """Every distinct label with how it parsed, before anything is touched.

        Production labels have been typed in dozens of shapes. Read this table
        first: it is the only chance to notice a label being read wrongly.
        """
        seen = {}
        for part in parts:
            seen.setdefault(part.label, self._letter(part))
        self.stdout.write(self.style.MIGRATE_HEADING('Labels as parsed'))
        for label, letter in sorted(seen.items(), key=lambda kv: str(kv[0])):
            parsed = parse_part_label(label or '')
            roman = parsed[1] if parsed and letter else None
            reading = f'({letter}){f" ({roman})" if roman else ""}' if letter \
                else self.style.ERROR('unreadable')
            self.stdout.write(f'  {label!r:16} -> {reading}')
        self.stdout.write('')

    def _report_unreadable(self, unreadable):
        if not unreadable:
            return
        self.stdout.write(self.style.WARNING(
            f'\n{len(unreadable)} part(s) skipped, left exactly as they are:'))
        for part in unreadable:
            label = (part.label or '').strip()
            match = _TWO_LETTERS.search(label)
            why = ('covers two letters' if match
                   and match.group(1).lower() != match.group(2).lower()
                   else 'label unreadable')
            self.stdout.write(
                f'  {part.question} {part.label!r} (id {part.pk}) - {why}')

    def _report_marks_to_check(self, totals):
        parts = ExamQuestionPart.objects.filter(
            max_marks__isnull=True).select_related('question__exam_paper')
        if not parts.exists():
            return
        self.stdout.write(self.style.WARNING(
            f'\n{parts.count()} part(s) have no marks. Fill them in on '
            f'/exam-papers/worksheet/parts/ or with auto_extract_marking_info:'))
        for part in parts[:40]:
            self.stdout.write(f'  {part.question} {part.label} (id {part.pk})')

    def _summarise(self, totals, groups):
        self.stdout.write('')
        line = (f"{len(groups)} group(s), {totals['groups']} to merge, "
                f"{totals['deleted']} part(s) deleted, "
                f"{totals['crops']} crop(s) stacked, "
                f"{totals['attempts']} attempt(s), "
                f"{totals['homework tasks']} task(s) and "
                f"{totals['work photos']} work photo(s) repointed.")
        if self.apply:
            self.stdout.write(self.style.SUCCESS(line))
        else:
            self.stdout.write(self.style.WARNING(
                line + '\nNothing was written. Re-run with --apply.'))
