import json

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from interactive_lessons.models import Topic

from . import log_tables_index
from .models import CheatSheet


class LogTablesIndexTests(TestCase):
    """The contents links are hand-measured, so guard their invariants."""

    def test_page_offset_round_trips(self):
        self.assertEqual(log_tables_index.to_printed_page(log_tables_index.to_pdf_page(33)), 33)

    def test_links_match_the_printed_contents(self):
        links = log_tables_index.get_contents_links()
        self.assertEqual(sorted(links), sorted(log_tables_index.CONTENTS_PDF_PAGES))
        # The booklet lists 15 maths sections and 14 physics/chemistry sections.
        self.assertEqual(len(links[6]), 15)
        self.assertEqual(len(links[7]), 14)

    def test_link_targets_are_in_range_ordered_and_on_the_page(self):
        for pdf_page, links in log_tables_index.get_contents_links().items():
            pages = [link["printed_page"] for link in links]
            self.assertEqual(pages, sorted(pages), f"page {pdf_page} rows are out of order")
            for link in links:
                self.assertGreaterEqual(link["printed_page"], log_tables_index.FIRST_PRINTED_PAGE)
                self.assertLessEqual(link["printed_page"], log_tables_index.LAST_PRINTED_PAGE)
                self.assertEqual(link["target"], log_tables_index.to_pdf_page(link["printed_page"]))
                # Rectangles are fractions of the page, so they must stay on it.
                self.assertGreaterEqual(link["x"], 0)
                self.assertGreaterEqual(link["y"], 0)
                self.assertLessEqual(link["x"] + link["w"], 1)
                self.assertLessEqual(link["y"] + link["h"], 1)

    def test_link_rows_do_not_overlap(self):
        for pdf_page, links in log_tables_index.get_contents_links().items():
            for earlier, later in zip(links, links[1:]):
                self.assertLessEqual(
                    earlier["y"] + earlier["h"],
                    later["y"],
                    f"rows for pages {earlier['printed_page']} and {later['printed_page']} overlap",
                )

    def test_viewer_context_is_json_ready(self):
        context = log_tables_index.viewer_context("/media/cheatsheets/LogTables.pdf")
        self.assertEqual(context["start_pdf_page"], log_tables_index.CONTENTS_PDF_PAGE)
        # Keys arrive as strings once JSON-encoded; the viewer looks them up by
        # page number, so check the round trip the browser actually sees.
        decoded = json.loads(context["contents_links"])
        self.assertIn(str(log_tables_index.CONTENTS_PDF_PAGE), decoded)
        self.assertEqual(json.loads(context["contents_pdf_pages"]), [6, 7])


class LogTablesViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="student", password="pw")
        self.client.force_login(self.user)
        topic = Topic.objects.create(name="Statistics", slug="statistics")
        self.cheatsheet = CheatSheet.objects.create(
            topic=topic,
            title="Log Tables",
            pdf_file="cheatsheets/LogTables.pdf",
        )

    def test_opens_on_the_contents_page_by_default(self):
        response = self.client.get(reverse("cheatsheets:log_tables"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["start_pdf_page"], log_tables_index.CONTENTS_PDF_PAGE)

    def test_start_page_does_not_depend_on_the_current_subject(self):
        """Every student gets the same booklet, opened at the same place."""
        maths = self.client.get(reverse("cheatsheets:log_tables"), {"subject": "maths"})
        physics = self.client.get(reverse("cheatsheets:log_tables"), {"subject": "physics"})
        self.assertEqual(maths.context["start_pdf_page"], physics.context["start_pdf_page"])

    def test_opens_on_a_requested_booklet_page(self):
        response = self.client.get(reverse("cheatsheets:log_tables"), {"page": 33})
        self.assertEqual(response.context["start_pdf_page"], log_tables_index.to_pdf_page(33))

    def test_out_of_range_and_junk_pages_fall_back_to_the_contents(self):
        for page in ("999", "0", "abc", ""):
            response = self.client.get(reverse("cheatsheets:log_tables"), {"page": page})
            self.assertEqual(
                response.context["start_pdf_page"],
                log_tables_index.CONTENTS_PDF_PAGE,
                f"page={page!r}",
            )

    def test_redirects_to_the_index_when_the_booklet_is_missing(self):
        self.cheatsheet.delete()
        response = self.client.get(reverse("cheatsheets:log_tables"))
        self.assertRedirects(
            response, reverse("cheatsheets:cheatsheets_index"), fetch_redirect_response=False
        )


class LogTablesPanelTagTests(TestCase):
    def setUp(self):
        self.topic = Topic.objects.create(name="Statistics", slug="statistics")

    def _render(self):
        from django.template import Context, Template

        return Template("{% load log_tables %}{% log_tables_panel %}").render(Context({}))

    def test_renders_the_launch_button_when_the_booklet_exists(self):
        CheatSheet.objects.create(
            topic=self.topic, title="Log Tables", pdf_file="cheatsheets/LogTables.pdf"
        )
        html = self._render()
        self.assertIn("lt-launch", html)
        self.assertIn("lt-restore", html)

    def test_renders_nothing_when_the_booklet_is_missing(self):
        self.assertEqual(self._render().strip(), "")


class SheetPagesTests(TestCase):
    """Summary Notes and Cheat Sheets each get their own page, per subject."""

    @classmethod
    def setUpTestData(cls):
        from core.models import Subject

        maths = Subject.objects.get(slug="maths")
        physics = Subject.objects.get(slug="physics")
        cls.algebra = Topic.objects.create(name="Algebra", slug="algebra-t", subject=maths)
        cls.optics = Topic.objects.create(name="Optics", slug="optics-t", subject=physics)
        cls.notes = CheatSheet.objects.create(
            topic=cls.algebra, kind=CheatSheet.KIND_SUMMARY_NOTES,
            title="Summary Notes", pdf_file="cheatsheets/notes-algebra.pdf",
        )
        cls.sheet = CheatSheet.objects.create(
            topic=cls.algebra, kind=CheatSheet.KIND_CHEAT_SHEET,
            title="Cheat Sheet", pdf_file="cheatsheets/cheat-algebra.pdf",
        )
        cls.log_tables = CheatSheet.objects.create(
            topic=cls.algebra, kind=CheatSheet.KIND_REFERENCE,
            title="Log Tables", pdf_file="cheatsheets/LogTables.pdf",
        )
        cls.physics_sheet = CheatSheet.objects.create(
            topic=cls.optics, kind=CheatSheet.KIND_CHEAT_SHEET,
            title="Cheat Sheet", pdf_file="cheatsheets/cheat-optics.pdf",
        )

    def setUp(self):
        self.client.force_login(User.objects.create_user(username="student", password="pw"))

    def _listed(self, url_name, **params):
        response = self.client.get(reverse(url_name), params)
        self.assertEqual(response.status_code, 200)
        return [sheet for _, sheets in response.context["topic_groups"] for sheet in sheets]

    def test_cheat_sheet_page_lists_only_cheat_sheets_for_the_subject(self):
        self.assertEqual(self._listed("cheatsheets:cheatsheets_index"), [self.sheet])

    def test_summary_notes_page_lists_only_summary_notes(self):
        self.assertEqual(self._listed("cheatsheets:summary_notes_index"), [self.notes])

    def test_physics_sees_only_physics_sheets(self):
        self.assertEqual(
            self._listed("cheatsheets:cheatsheets_index", subject="physics"), [self.physics_sheet]
        )

    def test_topic_page_has_a_section_per_kind_and_no_log_tables(self):
        response = self.client.get(reverse("cheatsheets:cheatsheets_topic", args=["algebra-t"]))
        sections = {heading: list(sheets) for heading, sheets in response.context["sections"]}
        self.assertEqual(sections, {"Summary Notes": [self.notes], "Cheat Sheet": [self.sheet]})

    def test_log_tables_found_by_kind(self):
        from .views import get_log_tables_cheatsheet

        self.assertEqual(get_log_tables_cheatsheet(), self.log_tables)


class SyncSheetsCommandTests(TestCase):
    """sync_sheets files every built PDF under its topics and clears out the rest."""

    def setUp(self):
        import tempfile
        from pathlib import Path

        from core.models import Subject
        from .management.commands.sync_sheets import CHEAT_SHEETS, SUMMARY_NOTES

        tmp = Path(tempfile.mkdtemp())
        self.media = tmp / 'media'
        self.notes_dir, self.sheets_dir = tmp / 'notes', tmp / 'sheets'
        for folder, mapping in ((self.notes_dir, SUMMARY_NOTES), (self.sheets_dir, CHEAT_SHEETS)):
            folder.mkdir()
            for stem in mapping:
                (folder / f'{stem}.pdf').write_bytes(b'%PDF-1.4 ' + stem.encode())
        maths = Subject.objects.get(slug='maths')
        slugs = {s for mapping in (SUMMARY_NOTES, CHEAT_SHEETS) for v in mapping.values() for s in v}
        self.topics = {s: Topic.objects.create(name=s, slug=s, subject=maths) for s in slugs}

    def _run(self, *extra):
        from io import StringIO

        from django.core.management import call_command
        from django.test import override_settings

        with override_settings(MEDIA_ROOT=str(self.media)):
            call_command('sync_sheets', '--notes-dir', str(self.notes_dir),
                         '--sheets-dir', str(self.sheets_dir), *extra, stdout=StringIO())

    def test_dry_run_writes_nothing(self):
        self._run()
        self.assertFalse(CheatSheet.objects.exists())

    def test_apply_files_one_of_each_kind_per_topic(self):
        self._run('--apply')
        stats = self.topics['descriptive-statistics']
        self.assertEqual(
            sorted(CheatSheet.objects.filter(topic=stats).values_list('kind', 'pdf_file')),
            [('cheat_sheet', 'cheatsheets/cheat-statistics-descriptive.pdf'),
             ('summary_notes', 'cheatsheets/notes-statistics.pdf')],
        )
        self.assertTrue((self.media / 'cheatsheets/cheat-algebra.pdf').is_file())
        # Re-running replaces in place rather than adding rows or suffixed files.
        count = CheatSheet.objects.count()
        self._run('--apply')
        self.assertEqual(CheatSheet.objects.count(), count)
        self.assertFalse(list(self.media.glob('cheatsheets/*_*.pdf')))

    def test_replaces_hand_uploaded_sheets_and_spares_log_tables(self):
        from core.models import Subject

        (self.media / 'cheatsheets').mkdir(parents=True)
        (self.media / 'cheatsheets/Old.pdf').write_bytes(b'%PDF old')
        algebra = self.topics['algebra']
        old = CheatSheet.objects.create(topic=algebra, kind=CheatSheet.KIND_CHEAT_SHEET,
                                        title='Main Cheat Sheet', pdf_file='cheatsheets/Old.pdf')
        stray_topic = Topic.objects.create(name='Random', slug='random-t',
                                           subject=Subject.objects.get(slug='maths'))
        stray = CheatSheet.objects.create(topic=stray_topic, kind=CheatSheet.KIND_CHEAT_SHEET,
                                          title='Cheat Sheet', pdf_file='cheatsheets/Stray.pdf')
        booklet = CheatSheet.objects.create(topic=algebra, kind=CheatSheet.KIND_REFERENCE,
                                            title='Log Tables', pdf_file='cheatsheets/LogTables.pdf')
        self._run('--apply', '--delete-legacy')
        old.refresh_from_db()
        self.assertEqual(old.pdf_file.name, 'cheatsheets/cheat-algebra.pdf')
        self.assertFalse((self.media / 'cheatsheets/Old.pdf').exists())
        self.assertFalse(CheatSheet.objects.filter(pk=stray.pk).exists())
        self.assertTrue(CheatSheet.objects.filter(pk=booklet.pk).exists())

    def test_missing_pdf_changes_nothing(self):
        from django.core.management.base import CommandError

        (self.sheets_dir / 'algebra.pdf').unlink()
        with self.assertRaises(CommandError):
            self._run('--apply')
        self.assertFalse(CheatSheet.objects.exists())
