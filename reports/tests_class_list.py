from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from homework.models import TeacherClass, TeacherProfile


class ClassListTests(TestCase):
    """My Classes lists each class's students, with View as for superusers."""

    @classmethod
    def setUpTestData(cls):
        cls.boss = User.objects.create_superuser('boss', 'boss@example.com', 'pw')
        boss_profile = TeacherProfile.objects.create(user=cls.boss, display_name='Mr Boss')
        cls.ava = User.objects.create_user('ava.pierce', first_name='Ava', last_name='Pierce')
        cls.liam = User.objects.create_user('liam.brennan', first_name='Liam', last_name='Brennan')
        cls.klass = TeacherClass.objects.create(teacher=boss_profile, name='6th')
        cls.klass.students.add(cls.ava, cls.liam)
        cls.teacher = User.objects.create_user('teach', password='pw', is_staff=True)
        own = TeacherClass.objects.create(
            teacher=TeacherProfile.objects.create(user=cls.teacher, display_name='Ms Teach'), name='5th')
        own.students.add(cls.ava)

    def test_superuser_sees_students_in_surname_order_with_view_as(self):
        self.client.force_login(self.boss)
        html = self.client.get(reverse('reports:dashboard')).content.decode()
        self.assertIn('Students (2)', html)
        self.assertLess(html.index('Liam Brennan'), html.index('Ava Pierce'))
        self.assertIn(f'name="user_pk" value="{self.ava.pk}"', html)
        self.assertIn(reverse('reports:student_report', args=[self.ava.pk]), html)

    def test_plain_teacher_sees_the_list_but_cannot_view_as(self):
        self.client.force_login(self.teacher)
        html = self.client.get(reverse('reports:dashboard')).content.decode()
        self.assertIn('Ava Pierce', html)
        self.assertNotIn('View as', html)

    def test_view_as_logs_in_as_the_student_and_lands_on_their_dashboard(self):
        self.client.force_login(self.boss)
        response = self.client.post(reverse('hijack:acquire'),
                                    {'user_pk': self.ava.pk, 'next': reverse('dashboard')})
        self.assertRedirects(response, reverse('dashboard'), fetch_redirect_response=False)
        self.assertEqual(int(self.client.session['_auth_user_id']), self.ava.pk)

    def test_stop_impersonating_returns_to_my_classes(self):
        self.client.force_login(self.boss)
        self.client.post(reverse('hijack:acquire'), {'user_pk': self.ava.pk, 'next': reverse('dashboard')})
        banner = self.client.get(reverse('dashboard')).content.decode()
        self.assertIn('stop impersonating', banner)
        self.assertNotIn('Overrides django-hijack', banner)
        self.assertIn(f'name="next" value="{reverse("reports:dashboard")}"', banner)
        response = self.client.post(reverse('hijack:release'), {'next': reverse('reports:dashboard')})
        self.assertRedirects(response, reverse('reports:dashboard'), fetch_redirect_response=False)
        self.assertEqual(int(self.client.session['_auth_user_id']), self.boss.pk)
