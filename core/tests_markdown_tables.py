"""Markdown tables carry the md-table class, and the built stylesheet styles it.

Without both halves a table in a question renders with its cells run together
("1015" for 10 and 15), which reads as a wrong number rather than a layout bug.
"""
from pathlib import Path

import markdown
from django.conf import settings
from django.test import SimpleTestCase

from core.markdown_tables import TableClassExtension
from interactive_lessons.views import render_math_markdown

TABLE = "| x | 0 | 5 |\n|---|---|---|\n| y | 1.0 | 1.2 |"


class MarkdownTableClassTests(SimpleTestCase):

    def test_question_text_tables_are_tagged(self):
        self.assertIn('<table class="md-table">', render_math_markdown(TABLE))

    def test_text_without_a_table_is_untouched(self):
        plain = markdown.markdown("Area is $\\pi r^2$.", extensions=["tables"])
        tagged = markdown.markdown("Area is $\\pi r^2$.", extensions=["tables", TableClassExtension()])
        self.assertEqual(plain, tagged)

    def test_the_built_stylesheet_styles_the_class(self):
        css = (Path(settings.BASE_DIR) / "static" / "css" / "tailwind.css").read_text()
        self.assertIn(".md-table", css, "run `npm run build:css` after editing static/src/input.css")
