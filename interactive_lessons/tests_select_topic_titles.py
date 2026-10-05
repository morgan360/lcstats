"""Exercises table titles: the short name shows, the full name and sub-topics hover."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from core.models import Subject
from interactive_lessons.models import Section, Topic
from interactive_lessons.views import topic_subtopics


class TopicTitleTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        maths = Subject.objects.get(slug='maths')
        cls.topic = Topic.objects.create(name='Descriptive Statistics', short_name='Descriptive Stats',
                                         subject=maths, paper='p2')
        # Production carries each section twice, once prefixed with the topic name.
        for i, name in enumerate(['Mean', 'Descriptive Statistics - Mean', 'Histograms',
                                  'Descriptive Statistics - Histograms']):
            Section.objects.create(topic=cls.topic, name=name, order=i)
        cls.levels = Topic.objects.create(name='Congruence & Proof', subject=maths, paper='p2')
        for i, name in enumerate(['Warm-up', 'Workout', 'Stretch']):
            Section.objects.create(topic=cls.levels, name=name, order=i)
        cls.user = User.objects.create_user('aoife', password='pw')

    def test_prefixed_duplicates_are_dropped(self):
        self.assertEqual(topic_subtopics(self.topic), ['Mean', 'Histograms'])

    def test_difficulty_levels_are_not_subtopics(self):
        self.assertEqual(topic_subtopics(self.levels), [])

    def test_blank_short_name_falls_back_to_name(self):
        self.assertEqual(self.levels.display_name, 'Congruence & Proof')

    def test_hover_lists_only_the_sections(self):
        self.client.force_login(self.user)
        html = self.client.get(reverse('select_topic')).content.decode()
        self.assertIn('Descriptive Stats', html)
        self.assertIn('<li>Histograms</li>', html)
        self.assertNotIn('Descriptive Statistics', html)

    def test_topic_without_sections_has_no_hover(self):
        self.client.force_login(self.user)
        html = self.client.get(reverse('select_topic')).content.decode()
        self.assertEqual(html.count('role="tooltip"'), 1)
