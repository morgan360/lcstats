from fractions import Fraction

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from core.models import Subject
from interactive_lessons.models import Topic, Section, Question
from interactive_lessons.services.utils_math import _preclean_plain, compare_algebraic
from interactive_lessons.stats_tutor import normalise_numeric_answer


class FractionAnswerTests(TestCase):
    """A typed fraction like "1/2" has to survive both grading paths.

    Both cleaners used to list ASCII "/" among the unicode superscripts, so
    every slash was swallowed into an exponent: "1/2" became "1**(/)2" for the
    algebraic path and "1^/2" for the numeric one. Neither parses, so every
    fraction answer fell through to the paid GPT fallback.
    """

    # Ground truth from the stdlib, not from our own normaliser.
    FRACTIONS = ["1/2", "3/4", "-2/3", "22/7", "10/5", "-3/11"]

    def test_preclean_leaves_ordinary_division_alone(self):
        for text in self.FRACTIONS:
            with self.subTest(text=text):
                self.assertEqual(_preclean_plain(text), text)

    def test_numeric_path_evaluates_fractions(self):
        for text in self.FRACTIONS:
            with self.subTest(text=text):
                self.assertEqual(
                    normalise_numeric_answer(text), [float(Fraction(text))]
                )

    def test_fraction_matches_its_decimal(self):
        for text in ["1/2", "3/4", "-1/4"]:
            with self.subTest(text=text):
                decimal = str(float(Fraction(text)))
                self.assertTrue(compare_algebraic(text, decimal))
                self.assertEqual(
                    normalise_numeric_answer(text),
                    normalise_numeric_answer(decimal),
                )

    def test_unsimplified_fraction_still_matches(self):
        self.assertTrue(compare_algebraic("2/4", "1/2"))

    def test_superscript_exponents_still_convert(self):
        # The slash entry existed to support "2⁵/²"; that must keep working,
        # and the exponent must be bracketed so it is not read as (2**5)/2.
        self.assertEqual(_preclean_plain("2⁵/²"), "2**(5/2)")
        self.assertEqual(normalise_numeric_answer("2⁵/²"), [2 ** 2.5])
        self.assertEqual(normalise_numeric_answer("2⁵"), [32.0])

    def test_slash_after_a_superscript_is_still_division(self):
        # "x²/3" is x squared over three, not x to the power of 2/3.
        self.assertEqual(_preclean_plain("x²/3"), "x**(2)/3")
        self.assertEqual(normalise_numeric_answer("3²/9"), [1.0])


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
