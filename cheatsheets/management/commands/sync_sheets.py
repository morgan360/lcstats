# cheatsheets/management/commands/sync_sheets.py
"""
Load the Summary Notes and Cheat Sheet PDFs built in the maths notes repo
(~/maths, see its CLAUDE.md) into CheatSheet rows, one of each per topic.

Usage:
    python manage.py sync_sheets                       # dry run: show what would change
    python manage.py sync_sheets --apply
    python manage.py sync_sheets --apply --delete-legacy
    python manage.py sync_sheets --notes-dir DIR --sheets-dir DIR --apply

Rows are keyed on (topic, kind), so re-running after a rebuild replaces the
PDFs in place; a row that pointed at some other PDF is taken over and that
file deleted once nothing uses it. --delete-legacy also removes any Cheat Sheet
row left on a topic this command does not fill. The Log Tables booklet is a
Reference row and is never touched.
"""

from pathlib import Path

from django.core.files import File
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError

from cheatsheets.models import CheatSheet
from interactive_lessons.models import Topic

# Built PDF stem -> the topics it is filed under. A notes section can cover
# more than one topic (Algebra, Trigonometry and Statistics are each split in
# two), in which case every topic gets the same PDF.
SUMMARY_NOTES = {
    'algebra': ['algebra', 'algebra-inequalities-and-factorisation'],
    'complex-numbers': ['complex-numbers'],
    'differentiation': ['differential-calculus'],
    'financial-maths': ['finance'],
    'functions': ['functions'],
    'geometry': ['geometry-theorems'],
    'indices-logs': ['indices-and-logs'],
    'integration': ['integration'],
    'length-area-volume': ['area-volume'],
    'probability': ['probability'],
    'proof-by-induction': ['proof-by-induction'],
    'sequences-series': ['sequences-and-series'],
    'statistics': ['descriptive-statistics', 'inferential-statistics'],
    'the-circle': ['the-circle'],
    'the-line': ['the-line'],
    'trigonometry': ['trignometry', 'trigonometry-2'],
}

CHEAT_SHEETS = dict(SUMMARY_NOTES)
del CHEAT_SHEETS['statistics']
CHEAT_SHEETS['statistics-descriptive'] = ['descriptive-statistics']
CHEAT_SHEETS['statistics-inferential'] = ['inferential-statistics']

# kind -> (row title, display order, file prefix under media/cheatsheets/)
KINDS = {
    CheatSheet.KIND_SUMMARY_NOTES: ('Summary Notes', 10, 'notes-'),
    CheatSheet.KIND_CHEAT_SHEET: ('Cheat Sheet', 20, 'cheat-'),
}

MATHS_BUILD = Path.home() / 'maths' / 'build'


class Command(BaseCommand):
    help = 'Load the Summary Notes and Cheat Sheet PDFs into CheatSheet rows'

    def add_arguments(self, parser):
        parser.add_argument(
            '--notes-dir', default=str(MATHS_BUILD / 'cheatsheets'),
            help='Folder of Summary Notes PDFs (default: ~/maths/build/cheatsheets)',
        )
        parser.add_argument(
            '--sheets-dir', default=str(MATHS_BUILD / 'cheatsheets-short'),
            help='Folder of Cheat Sheet PDFs (default: ~/maths/build/cheatsheets-short)',
        )
        parser.add_argument('--apply', action='store_true', help='Write changes (default is a dry run)')
        parser.add_argument(
            '--delete-legacy', action='store_true',
            help='Also delete Cheat Sheet rows not produced by this command, with their files',
        )

    def handle(self, *args, **options):
        apply = options['apply']
        plan = [
            (CheatSheet.KIND_SUMMARY_NOTES, Path(options['notes_dir']), SUMMARY_NOTES),
            (CheatSheet.KIND_CHEAT_SHEET, Path(options['sheets_dir']), CHEAT_SHEETS),
        ]

        # Check everything before writing anything, so a missing PDF or topic
        # cannot leave the site half-updated.
        topics = {t.slug: t for t in Topic.objects.all()}
        problems = []
        for kind, folder, mapping in plan:
            for stem, slugs in mapping.items():
                if not (folder / f'{stem}.pdf').is_file():
                    problems.append(f'missing PDF: {folder / stem}.pdf')
                problems += [f'no topic with slug {s!r} (for {stem})' for s in slugs if s not in topics]
        if problems:
            raise CommandError('Nothing changed:\n  ' + '\n  '.join(problems))

        if not apply:
            self.stdout.write(self.style.WARNING('Dry run -- pass --apply to write.'))

        produced = set()
        self.taken_over = set()
        for kind, folder, mapping in plan:
            title, order, prefix = KINDS[kind]
            for stem, slugs in mapping.items():
                name = f'cheatsheets/{prefix}{stem}.pdf'
                produced.add(name)
                if apply:
                    self._store(folder / f'{stem}.pdf', name)
                for slug in slugs:
                    self._upsert(topics[slug], kind, title, order, name, apply)

        if options['delete_legacy']:
            legacy = (CheatSheet.objects.filter(kind=CheatSheet.KIND_CHEAT_SHEET)
                      .exclude(pdf_file__in=produced).exclude(pk__in=self.taken_over))
            for sheet in legacy.select_related('topic'):
                self.stdout.write(f'  delete  {sheet.topic.slug:40} {sheet.title} ({sheet.pdf_file.name})')
                if apply:
                    name = sheet.pdf_file.name
                    sheet.delete()
                    if name and not CheatSheet.objects.filter(pdf_file=name).exists():
                        default_storage.delete(name)

        self.stdout.write(self.style.SUCCESS('Done.' if apply else 'Dry run complete.'))

    def _store(self, source, name):
        """Write the PDF to media under exactly `name`, replacing any old copy."""
        if default_storage.exists(name):
            default_storage.delete(name)
        with source.open('rb') as fh:
            saved = default_storage.save(name, File(fh))
        if saved != name:
            raise CommandError(f'storage saved {source} as {saved}, not {name}')

    def _upsert(self, topic, kind, title, order, name, apply):
        sheet = CheatSheet.objects.filter(topic=topic, kind=kind).order_by('id').first()
        action = 'create' if sheet is None else 'update'
        detail = f'  (was {sheet.pdf_file.name})' if sheet and sheet.pdf_file.name != name else ''
        self.stdout.write(f'  {action}  {topic.slug:40} {title:14} {name}{detail}')
        if sheet is not None:
            self.taken_over.add(sheet.pk)
        if not apply:
            return
        if sheet is None:
            sheet = CheatSheet(topic=topic, kind=kind)
        old_name = sheet.pdf_file.name
        sheet.title = title
        sheet.order = order
        sheet.pdf_file.name = name
        sheet.save()
        # A row taken over from a hand-uploaded PDF leaves that file behind.
        if old_name and old_name != name and not CheatSheet.objects.filter(pdf_file=old_name).exists():
            self.stdout.write(f'  remove  {old_name}')
            default_storage.delete(old_name)
