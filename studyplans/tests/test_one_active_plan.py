"""One active plan per student: enforced in the database, explained in the UI.

The rule is phrased through a sentinel column rather than a condition on
status, because MySQL accepts a conditional unique constraint and then silently
builds nothing. These tests therefore check the database actually refuses a
second plan, not merely that the model says it will.
"""
from datetime import timedelta

from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import Subject
from homework.models import TeacherClass, TeacherProfile
from interactive_lessons.models import Topic
from studyplans.models import StudyPlan


def make_teacher(username):
    user = User.objects.create_user(username=username, password='pw', is_staff=True)
    group, _ = Group.objects.get_or_create(name='Teachers')
    user.groups.add(group)
    profile, _ = TeacherProfile.objects.get_or_create(user=user)
    return user, profile


def make_student(username):
    user = User.objects.create_user(username=username, password='pw')
    group, _ = Group.objects.get_or_create(name='Students')
    user.groups.add(group)
    return user


class OneActivePlanTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.maths = Subject.objects.get(slug='maths')
        cls.physics = Subject.objects.filter(slug='physics').first()
        cls.teacher_user, cls.teacher = make_teacher('ms_teacher')
        cls.student = make_student('aoife')
        cls.other = make_student('brian')
        cls.today = timezone.localdate()

    def plan(self, student=None, status='active', title='Plan', subject=None):
        return StudyPlan.objects.create(
            student=student or self.student, teacher=self.teacher,
            subject=subject or self.maths, title=title,
            start_date=self.today, deadline=self.today + timedelta(days=14),
            status=status)


class TheRuleTests(OneActivePlanTestBase):

    def test_the_database_refuses_a_second_active_plan(self):
        self.plan(title='First')
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                StudyPlan.objects.create(
                    student=self.student, teacher=self.teacher,
                    subject=self.maths, title='Second',
                    start_date=self.today,
                    deadline=self.today + timedelta(days=14), status='active')

    def test_the_constraint_is_really_in_the_database(self):
        """MySQL silently skips conditional unique constraints -- check it exists."""
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM information_schema.STATISTICS "
                "WHERE TABLE_SCHEMA = DATABASE() "
                "AND TABLE_NAME = 'studyplans_studyplan' "
                "AND INDEX_NAME = 'studyplan_one_active_per_student' "
                "AND NON_UNIQUE = 0")
            self.assertGreater(cursor.fetchone()[0], 0,
                               "the unique index was never created")

    def test_clean_explains_the_clash_before_the_database_does(self):
        self.plan(title='Christmas Push')
        second = StudyPlan(
            student=self.student, teacher=self.teacher, subject=self.maths,
            title='Another', start_date=self.today,
            deadline=self.today + timedelta(days=14), status='active')
        with self.assertRaises(ValidationError) as caught:
            second.full_clean()
        self.assertIn('Christmas Push', str(caught.exception))

    def test_drafts_and_archives_do_not_take_the_slot(self):
        self.plan(status='draft', title='Draft')
        self.plan(status='archived', title='Old')
        self.plan(status='completed', title='Finished')
        live = self.plan(title='Live')          # must not raise
        self.assertEqual(live.active_slot, self.student.id)
        self.assertEqual(
            StudyPlan.objects.filter(student=self.student).count(), 4)

    def test_two_students_may_each_have_one(self):
        self.plan(student=self.student)
        self.plan(student=self.other)  # must not raise

    def test_archiving_frees_the_slot(self):
        first = self.plan(title='First')
        first.archive()
        second = self.plan(title='Second')
        self.assertEqual(second.active_slot, self.student.id)
        first.refresh_from_db()
        self.assertIsNone(first.active_slot)

    def test_the_slot_follows_status_on_every_save(self):
        plan = self.plan()
        self.assertEqual(plan.active_slot, self.student.id)
        plan.status = 'completed'
        plan.save(update_fields=['status'])
        plan.refresh_from_db()
        self.assertIsNone(plan.active_slot,
                          "update_fields must not skip the sentinel")

    def test_a_plan_per_subject_is_not_allowed_either(self):
        """Deliberate: the rule is per student, not per subject."""
        if self.physics is None:
            self.skipTest("no physics subject in this database")
        self.plan(subject=self.maths, title='Maths plan')
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                StudyPlan.objects.create(
                    student=self.student, teacher=self.teacher,
                    subject=self.physics, title='Physics plan',
                    start_date=self.today,
                    deadline=self.today + timedelta(days=14), status='active')


class TeacherExperienceTests(OneActivePlanTestBase):

    def setUp(self):
        self.klass = TeacherClass.objects.create(
            teacher=self.teacher, name='6th Year')
        self.klass.students.add(self.student, self.other)
        self.topic = Topic.objects.create(
            name='Integration', subject=self.maths, paper='p1')
        self.client.force_login(self.teacher_user)

    def builder_post(self, **overrides):
        data = {
            'title': 'New plan',
            'start_date': self.today.isoformat(),
            'deadline': (self.today + timedelta(days=21)).isoformat(),
            'weekly_minutes': '120',
            'topics': [str(self.topic.id)],
            f'target_{self.topic.id}': '75',
            f'priority_{self.topic.id}': '1',
            f'size_{self.topic.id}': '2',
        }
        data.update(overrides)
        return data

    def test_making_a_second_plan_is_refused_with_a_message(self):
        existing = self.plan(title='Christmas Push')
        response = self.client.post(
            reverse('studyplans:plan_create'),
            self.builder_post(student=str(self.student.id)), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            StudyPlan.objects.filter(student=self.student).count(), 1)
        text = " ".join(str(m) for m in response.context['messages'])
        self.assertIn('Christmas Push', text)

    def test_a_rollout_leaves_students_who_are_already_on_a_plan(self):
        self.plan(student=self.student, title='Christmas Push')
        self.client.post(reverse('studyplans:plan_create'),
                         self.builder_post(teacher_class=str(self.klass.id)),
                         follow=True)
        self.assertEqual(
            StudyPlan.objects.filter(student=self.student).count(), 1,
            "aoife was mid-plan and should have been left alone")
        self.assertTrue(
            StudyPlan.objects.filter(student=self.other, status='active').exists(),
            "brian was free and should have got one")

    def test_a_teacher_can_archive_to_free_the_slot(self):
        plan = self.plan(title='Christmas Push')
        self.client.post(
            reverse('studyplans:set_plan_status', args=[plan.id]),
            {'action': 'archive'})
        plan.refresh_from_db()
        self.assertEqual(plan.status, 'archived')
        self.assertIsNone(plan.active_slot)

    def test_a_teacher_can_promote_a_draft(self):
        draft = self.plan(status='draft', title='Draft')
        self.client.post(
            reverse('studyplans:set_plan_status', args=[draft.id]),
            {'action': 'activate'})
        draft.refresh_from_db()
        self.assertEqual(draft.status, 'active')

    def test_promoting_a_draft_is_refused_while_another_is_live(self):
        self.plan(title='Christmas Push')
        draft = self.plan(status='draft', title='Draft')
        response = self.client.post(
            reverse('studyplans:set_plan_status', args=[draft.id]),
            {'action': 'activate'}, follow=True)
        draft.refresh_from_db()
        self.assertEqual(draft.status, 'draft')
        text = " ".join(str(m) for m in response.context['messages'])
        self.assertIn('Christmas Push', text)
