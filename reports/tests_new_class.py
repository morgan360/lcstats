from django.contrib.auth.models import Permission, User
from django.test import TestCase
from django.urls import reverse

from homework.models import TeacherClass, TeacherProfile


class NewClassButtonTests(TestCase):
    """My Classes links to the admin's add-class form and comes back after."""

    @classmethod
    def setUpTestData(cls):
        cls.boss = User.objects.create_superuser('boss', 'boss@example.com', 'pw')
        cls.profile = TeacherProfile.objects.create(user=cls.boss, display_name='Mr Boss')

    def test_button_prefills_the_teacher_and_returns_here(self):
        self.client.force_login(self.boss)
        html = self.client.get(reverse('reports:dashboard')).content.decode()
        self.assertIn('+ New class', html)
        self.assertIn(f'{reverse("admin:homework_teacherclass_add")}?next=%2Freports%2F'
                      f'&amp;teacher={self.profile.pk}', html)

    def test_no_button_without_permission(self):
        teacher = User.objects.create_user('teach', password='pw', is_staff=True)
        TeacherProfile.objects.create(user=teacher, display_name='Ms Teach')
        self.client.force_login(teacher)
        self.assertNotIn('New class', self.client.get(reverse('reports:dashboard')).content.decode())

    def test_button_shows_for_a_teacher_with_the_permission(self):
        teacher = User.objects.create_user('teach', password='pw', is_staff=True)
        TeacherProfile.objects.create(user=teacher, display_name='Ms Teach')
        teacher.user_permissions.add(Permission.objects.get(codename='add_teacherclass'))
        self.client.force_login(teacher)
        self.assertIn('+ New class', self.client.get(reverse('reports:dashboard')).content.decode())

    def _add(self, next_url):
        self.client.force_login(self.boss)
        url = f"{reverse('admin:homework_teacherclass_add')}?next={next_url}"
        return self.client.post(url, {'teacher': self.profile.pk, 'name': '6th Year Maths',
                                      'description': '', 'is_active': 'on'})

    def test_saving_returns_to_my_classes(self):
        response = self._add('/reports/')
        self.assertRedirects(response, reverse('reports:dashboard'), fetch_redirect_response=False)
        self.assertTrue(TeacherClass.objects.filter(name='6th Year Maths', teacher=self.profile).exists())

    def test_offsite_next_is_ignored(self):
        response = self._add('https://evil.example.com/')
        self.assertEqual(response.status_code, 302)
        self.assertNotIn('evil.example.com', response['Location'])
