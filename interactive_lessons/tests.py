from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from core.models import Subject
from interactive_lessons.models import Topic, Section, Question


class MoveSectionAdminTests(TestCase):
    """Moving a section between topics has to take its questions with it."""

    @classmethod
    def setUpTestData(cls):
        # Migrations seed the subjects, so take the existing row if it's there.
        cls.subject, _ = Subject.objects.get_or_create(
            name="Maths", defaults={"slug": "maths"}
        )
        cls.old_topic = Topic.objects.create(subject=cls.subject, name="Trigonometry")
        cls.new_topic = Topic.objects.create(subject=cls.subject, name="Geometry")
        cls.section = Section.objects.create(topic=cls.old_topic, name="Sine Rule")
        cls.question = Question.objects.create(topic=cls.old_topic, section=cls.section)
        cls.admin_user = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="pw"
        )

    def setUp(self):
        self.client.force_login(self.admin_user)

    def test_change_form_move_takes_questions_along(self):
        url = reverse("admin:interactive_lessons_section_change", args=[self.section.pk])
        response = self.client.post(url, {
            "name": self.section.name,
            "topic": self.new_topic.pk,
            "order": self.section.order,
        })
        self.assertEqual(response.status_code, 302)
        self.section.refresh_from_db()
        self.question.refresh_from_db()
        self.assertEqual(self.section.topic, self.new_topic)
        self.assertEqual(self.question.topic, self.new_topic)

    def test_action_moves_selected_sections(self):
        url = reverse("admin:interactive_lessons_section_changelist")
        response = self.client.post(url, {
            "action": "move_to_topic",
            "_selected_action": [str(self.section.pk)],
            "topic": self.new_topic.pk,
            "apply": "Move sections",
        })
        self.assertEqual(response.status_code, 302)
        self.section.refresh_from_db()
        self.question.refresh_from_db()
        self.assertEqual(self.section.topic, self.new_topic)
        self.assertEqual(self.question.topic, self.new_topic)

    def test_action_confirmation_page_lists_the_selection(self):
        url = reverse("admin:interactive_lessons_section_changelist")
        response = self.client.post(url, {
            "action": "move_to_topic",
            "_selected_action": [str(self.section.pk)],
        })
        self.assertContains(response, "Sine Rule")
        self.section.refresh_from_db()
        self.assertEqual(self.section.topic, self.old_topic)

    def test_action_refuses_a_name_clash(self):
        Section.objects.create(topic=self.new_topic, name="Sine Rule")
        url = reverse("admin:interactive_lessons_section_changelist")
        response = self.client.post(url, {
            "action": "move_to_topic",
            "_selected_action": [str(self.section.pk)],
            "topic": self.new_topic.pk,
            "apply": "Move sections",
        })
        self.assertEqual(response.status_code, 200)
        self.section.refresh_from_db()
        self.assertEqual(self.section.topic, self.old_topic)
