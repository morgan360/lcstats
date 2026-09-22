"""Admin pages for study plans.

Admin is for looking and for the occasional repair; plans are built at
/study-plans/teacher/new/. These tests hold that line: the pages a teacher may
land on must render, and weeks -- which nothing reads any more -- must not be
on offer to edit.
"""
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import Subject
from homework.models import TeacherProfile
from interactive_lessons.models import Topic
from studyplans.models import (
    StudyPlan, StudyPlanGoal, StudyPlanMicroBadge,
)


class StudyPlanAdminTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        maths = Subject.objects.get(slug='maths')
        topic = Topic.objects.create(name='Algebra', subject=maths, paper='p1')
        teacher = User.objects.create_user('ms_teacher', password='pw', is_staff=True)
        profile, _ = TeacherProfile.objects.get_or_create(user=teacher)
        student = User.objects.create_user('aoife', password='pw')
        cls.admin = User.objects.create_superuser('boss', 'boss@example.com', 'pw')

        today = timezone.localdate()
        cls.plan = StudyPlan.objects.create(
            student=student, teacher=profile, subject=maths, title='Plan',
            start_date=today, deadline=today + timedelta(days=42), status='active')
        cls.goal = StudyPlanGoal.objects.create(plan=cls.plan, topic=topic)
        cls.badge = StudyPlanMicroBadge.objects.create(
            goal=cls.goal, number=1, target_date=today + timedelta(days=4))

    def setUp(self):
        self.client.force_login(self.admin)

    def test_the_pages_render(self):
        for url in (
            reverse('admin:studyplans_studyplan_changelist'),
            reverse('admin:studyplans_studyplan_change', args=[self.plan.id]),
            reverse('admin:studyplans_studyplanmicrobadge_changelist'),
            reverse('admin:studyplans_studyplanmicrobadge_change', args=[self.badge.id]),
            reverse('admin:studyplans_studyplangoal_change', args=[self.goal.id]),
        ):
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_weeks_are_not_on_offer(self):
        response = self.client.get(reverse('admin:index'))
        self.assertNotContains(response, 'Study Plan Weeks')
        self.assertContains(response, 'MicroBadge')

    def test_an_item_cannot_be_given_a_week(self):
        from studyplans.admin import StudyPlanItemAdmin
        self.assertIn('week', StudyPlanItemAdmin.exclude)
