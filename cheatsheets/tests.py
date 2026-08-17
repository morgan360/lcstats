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
