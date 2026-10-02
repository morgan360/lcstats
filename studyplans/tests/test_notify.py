"""A student is emailed once, when a study plan goes live for them."""
from django.core import mail
from django.test import override_settings
from django.urls import reverse

from studyplans.models import StudyPlan

from .test_views import ViewTestBase


@override_settings(SITE_URL='https://www.numscoil.ie')
class PlanEmailTests(ViewTestBase):

    def setUp(self):
        for user, address in ((self.student, 'aoife@example.com'),
                              (self.classmate, 'brian@example.com')):
            user.email = address
            user.save(update_fields=['email'])
        self.client.force_login(self.teacher_user)

    def create(self, **extra):
        data = self.builder_post(student=str(self.classmate.id))
        data.update(extra)
        return self.client.post(reverse('studyplans:plan_create'), data)

    def test_a_plan_set_live_emails_the_student(self):
        self.create()
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ['brian@example.com'])
        self.assertIn('Spring plan', message.subject)
        self.assertIn('https://www.numscoil.ie/study-plans/', message.body)
        self.assertIn('Integration', message.body)

    def test_a_draft_emails_nobody_until_it_is_made_active(self):
        self.create(save='draft')
        self.assertEqual(len(mail.outbox), 0)

        plan = StudyPlan.objects.get(student=self.classmate, title='Spring plan')
        self.client.post(reverse('studyplans:set_plan_status', args=[plan.id]),
                         {'action': 'activate'})
        self.assertEqual(len(mail.outbox), 1)

    def test_activating_again_does_not_email_twice(self):
        self.create()
        plan = StudyPlan.objects.get(student=self.classmate, title='Spring plan')
        plan.archive()
        self.client.post(reverse('studyplans:set_plan_status', args=[plan.id]),
                         {'action': 'activate'})
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(plan.events.filter(kind='notified').count(), 1)

    def test_a_class_rollout_emails_each_student_who_gets_a_plan(self):
        """aoife already holds the fixture plan, so only brian is given one."""
        data = self.builder_post(teacher_class=str(self.klass.id))
        self.client.post(reverse('studyplans:plan_create'), data)
        self.assertEqual([m.to[0] for m in mail.outbox], ['brian@example.com'])

    def test_a_student_without_an_address_is_skipped_and_the_teacher_told(self):
        self.classmate.email = ''
        self.classmate.save(update_fields=['email'])
        response = self.create()
        self.assertEqual(len(mail.outbox), 0)
        self.assertTrue(StudyPlan.objects.filter(
            student=self.classmate, title='Spring plan', status='active').exists())
        notes = [str(m) for m in response.wsgi_request._messages]
        self.assertTrue(any('no email address' in n for n in notes), notes)
