"""Students are emailed when homework is published -- through the admin Add form.

Assignments are created already published, in one save on the Add page. The
email used to fire only for an edit from unpublished to published, so from the
single-save flow onward (cdf95f64) almost no assignment emailed anyone: 5 of 44
on production. These tests drive the real Add form, the path teachers use.
"""
import re
from datetime import timedelta

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone

from core.models import Subject
from homework.models import HomeworkAssignment, TeacherClass, TeacherProfile
from homework.services import notify_if_newly_published
from interactive_lessons.models import Topic

ADD_URL = '/admin/homework/homeworkassignment/add/'


@override_settings(SITE_URL='https://www.numscoil.ie')
class PublishedEmailTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.maths = Subject.objects.get(slug='maths')
        cls.topic = Topic.objects.create(name='Integration', subject=cls.maths, paper='p1')
        cls.admin = User.objects.create_superuser('admin', 'admin@example.com', 'pw')
        cls.teacher = TeacherProfile.objects.create(user=cls.admin, display_name='Ms Teacher')
        cls.klass = TeacherClass.objects.create(teacher=cls.teacher, name='6th Year A')
        cls.aoife = User.objects.create_user('aoife', 'aoife@example.com', 'pw')
        cls.brian = User.objects.create_user('brian', 'brian@example.com', 'pw')
        cls.ciara = User.objects.create_user('ciara', '', 'pw')  # no address
        cls.klass.students.add(cls.aoife, cls.brian, cls.ciara)

    def setUp(self):
        self.client.force_login(self.admin)

    def add_form(self, **fields):
        """POST the Add page as a teacher would, with every inline left empty."""
        page = self.client.get(ADD_URL).content.decode()
        data = {}
        for prefix in set(re.findall(r'name="([\w-]+)-TOTAL_FORMS"', page)):
            data.update({f'{prefix}-TOTAL_FORMS': '0', f'{prefix}-INITIAL_FORMS': '0',
                         f'{prefix}-MIN_NUM_FORMS': '0', f'{prefix}-MAX_NUM_FORMS': '1000'})
        due = timezone.localtime() + timedelta(days=2)
        now = timezone.localtime()
        data.update({
            'teacher': self.teacher.id, 'topic': self.topic.id,
            'title': 'Integration week 1', 'description': '',
            'assigned_date_0': now.strftime('%Y-%m-%d'), 'assigned_date_1': now.strftime('%H:%M:%S'),
            'due_date_0': due.strftime('%Y-%m-%d'), 'due_date_1': due.strftime('%H:%M:%S'),
            'assigned_classes': [self.klass.id],
            '_save': 'Save',
        })
        data.update(fields)
        return self.client.post(ADD_URL, data)

    def test_creating_it_published_emails_the_class(self):
        response = self.add_form(is_published='on')
        if response.status_code != 302:  # the form was rejected: show why
            self.fail(response.context['adminform'].form.errors)
        self.assertEqual(sorted(m.to[0] for m in mail.outbox),
                         ['aoife@example.com', 'brian@example.com'])
        assignment = HomeworkAssignment.objects.get(title='Integration week 1')
        self.assertTrue(assignment.notification_sent)

    def test_the_link_is_to_the_real_site(self):
        self.add_form(is_published='on')
        assignment = HomeworkAssignment.objects.get(title='Integration week 1')
        self.assertIn(f'https://www.numscoil.ie/homework/assignment/{assignment.id}/',
                      mail.outbox[0].body)
        self.assertNotIn('numscoil.com', mail.outbox[0].body)

    def test_a_draft_emails_nobody_until_it_is_published(self):
        self.add_form()
        self.assertEqual(len(mail.outbox), 0)
        assignment = HomeworkAssignment.objects.get(title='Integration week 1')
        self.assertFalse(assignment.notification_sent)

        assignment.is_published = True
        assignment.save()
        notify_if_newly_published(assignment)
        self.assertEqual(len(mail.outbox), 2)

    def test_saving_again_does_not_email_twice(self):
        self.add_form(is_published='on')
        assignment = HomeworkAssignment.objects.get(title='Integration week 1')
        self.assertIsNone(notify_if_newly_published(assignment))
        self.assertEqual(len(mail.outbox), 2)

    def test_an_assignment_past_its_due_date_is_never_emailed(self):
        old = HomeworkAssignment.objects.create(
            teacher=self.teacher, topic=self.topic, title='Last term',
            due_date=timezone.now() - timedelta(days=30), is_published=True)
        old.assigned_classes.add(self.klass)
        self.assertIsNone(notify_if_newly_published(old))
        self.assertEqual(len(mail.outbox), 0)
