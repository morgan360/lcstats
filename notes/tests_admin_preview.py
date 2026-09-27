"""The rendered answer preview on an InfoBot query's admin page."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from notes.admin import render_answer
from notes.models import InfoBotQuery

ANSWER = r"$P'(t)$ is the derivative. Differentiate $P(t)=0.82-0.12\ln(t+1)$, **then** put $t=1$."


class RenderAnswerTests(TestCase):
    def test_markdown_is_formatted_and_maths_left_for_katex(self):
        html = render_answer(ANSWER)
        self.assertIn("<strong>then</strong>", html)
        self.assertIn(r"$P(t)=0.82-0.12\ln(t+1)$", html)

    def test_html_from_the_chat_is_kept_as_it_was(self):
        self.assertEqual(render_answer("<p>Use $x^2$</p>"), "<p>Use $x^2$</p>")

    def test_scripts_and_attributes_are_stripped(self):
        html = render_answer('<p onclick="steal()">hi</p><script>steal()</script>'
                             '<img src=x onerror="steal()">')
        self.assertNotIn("<script", html)
        self.assertNotIn("onclick", html)
        self.assertNotIn("onerror", html)
        self.assertNotIn("<img", html)

    def test_a_blank_answer_renders_empty(self):
        self.assertEqual(render_answer(None), "")


class AdminPageTests(TestCase):
    def test_change_page_shows_the_preview_with_katex(self):
        admin = User.objects.create_superuser("admin", password="pw")
        query = InfoBotQuery.objects.create(question="come si calcola", answer=ANSWER)
        self.client.force_login(admin)
        response = self.client.get(
            reverse("admin:notes_infobotquery_change", args=[query.pk]))
        self.assertContains(response, "Answer as the student saw it")
        self.assertContains(response, '<div class="infobot-preview"><p>')
        self.assertContains(response, "katex.min.js")
        self.assertContains(response, "admin/js/infobot_preview.js")
