"""Stamp cards: filled only from plan MicroBadges and passed Badge Tests.

A topic never on a plan shows a blank card; a topic on several plans shows the
best of them; and a card can only move forward.
"""
from datetime import timedelta

from django.contrib.auth.models import Group, User
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from core.models import Subject
from homework.models import TeacherProfile
from interactive_lessons.models import Topic
from studyplans.models import (
    StudyPlan, StudyPlanCheckpoint, StudyPlanGoal, StudyPlanMicroBadge,
)
from studyplans.services import stamps


class StampTestBase(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.maths = Subject.objects.get(slug='maths')
        cls.topic = Topic.objects.create(
            name='Probability', subject=cls.maths, paper='p2')
        cls.other_topic = Topic.objects.create(
            name='Geometry', subject=cls.maths, paper='p2')
        cls.student = User.objects.create_user('aoife', password='pw')
        Group.objects.get_or_create(name='Students')[0].user_set.add(cls.student)
        teacher = User.objects.create_user('ms_teacher', password='pw', is_staff=True)
        cls.teacher, _ = TeacherProfile.objects.get_or_create(user=teacher)

    def plan_goal(self, status='active', earned=0, topic=None, title='Plan'):
        today = timezone.localdate()
        plan = StudyPlan.objects.create(
            student=self.student, teacher=self.teacher, subject=self.maths,
            title=title, start_date=today, deadline=today + timedelta(days=70),
            status=status)
        goal = StudyPlanGoal.objects.create(plan=plan, topic=topic or self.topic)
        for n in range(1, 11):
            StudyPlanMicroBadge.objects.create(
                goal=goal, number=n, target_date=today + timedelta(days=6 * n),
                earned_at=timezone.now() if n <= earned else None)
        return goal

    def card(self, topic=None):
        topic = topic or self.topic
        return next(c for c in stamps.cards_for(self.student, self.maths)
                    if c['topic'] == topic)


class CardTests(StampTestBase):

    def test_a_topic_never_on_a_plan_is_blank(self):
        card = self.card(self.other_topic)
        self.assertFalse(card['on_plan'])
        self.assertEqual(card['micro'], [False] * 10)
        self.assertFalse(card['stamped'])

    def test_earned_microbadges_fill_the_card(self):
        self.plan_goal(earned=4)
        card = self.card()
        self.assertTrue(card['on_plan'])
        self.assertEqual(card['microstamps'], 4)
        self.assertEqual(card['micro'], [True] * 4 + [False] * 6)

    def test_a_passed_badge_test_stamps_it_even_on_an_archived_plan(self):
        goal = self.plan_goal(status='archived', earned=10)
        StudyPlanCheckpoint.objects.create(
            goal=goal, round=1, status='passed', pass_mark=75, score=82,
            sat_at=timezone.now())
        card = self.card()
        self.assertTrue(card['stamped'])
        self.assertEqual(card['score'], 82)

    def test_a_failed_or_voided_test_does_not(self):
        goal = self.plan_goal(earned=10)
        StudyPlanCheckpoint.objects.create(
            goal=goal, round=1, status='failed', pass_mark=75, score=40,
            sat_at=timezone.now())
        StudyPlanCheckpoint.objects.create(
            goal=goal, round=2, status='voided', pass_mark=75, score=90,
            sat_at=timezone.now())
        self.assertFalse(self.card()['stamped'])

    def test_the_best_of_several_plans_is_shown(self):
        self.plan_goal(status='archived', earned=7, title='Old')
        self.plan_goal(status='active', earned=2, title='New')
        self.assertEqual(self.card()['microstamps'], 7)

    def test_a_draft_plan_does_not_fill_the_card(self):
        self.plan_goal(status='draft', earned=5)
        self.assertFalse(self.card()['on_plan'])

    def test_retry_microbadges_are_not_counted_among_the_ten(self):
        goal = self.plan_goal(earned=10)
        StudyPlanMicroBadge.objects.create(
            goal=goal, number=11, kind='retry',
            target_date=timezone.localdate(), earned_at=timezone.now())
        self.assertEqual(self.card()['microstamps'], 10)

    def test_another_students_plan_is_not_mine(self):
        other = User.objects.create_user('brian', password='pw')
        goal = self.plan_goal(earned=6)
        goal.plan.student = other
        goal.plan.save(update_fields=['student'])
        self.assertFalse(self.card()['on_plan'])

    def test_queries_do_not_grow_with_topics(self):
        self.plan_goal(earned=3)
        with CaptureQueriesContext(connection) as one:
            stamps.cards_for(self.student, self.maths)
        for n in range(3):
            topic = Topic.objects.create(name=f'Extra {n}', subject=self.maths,
                                         paper='p1')
            self.plan_goal(status='archived', earned=n, topic=topic, title=f'X{n}')
        with CaptureQueriesContext(connection) as many:
            stamps.cards_for(self.student, self.maths)
        self.assertEqual(len(one), len(many))


class StampPageTests(StampTestBase):

    def setUp(self):
        self.client.force_login(self.student)

    def test_stamp_cards_page_lists_every_topic(self):
        self.plan_goal(earned=3)
        response = self.client.get(reverse('studyplans:stamp_cards'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '3 of 10 MicroBadges')
        self.assertContains(response, 'Not on a plan yet')

    def test_dashboard_shows_topics_on_a_plan(self):
        self.plan_goal(earned=1)
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual([c['topic'] for c in response.context['stamp_cards']],
                         [self.topic])
