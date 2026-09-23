"""The Staff menu's New Homework link (templates/_base.html)."""
from django.contrib.auth.models import Permission, User
from django.test import TestCase
from django.urls import reverse


class NewHomeworkMenuLinkTests(TestCase):

    def setUp(self):
        self.add_url = reverse('admin:homework_homeworkassignment_add')

    def test_staff_who_can_create_homework_get_the_link(self):
        user = User.objects.create_user('t', password='pw', is_staff=True)
        user.user_permissions.add(Permission.objects.get(codename='add_homeworkassignment'))
        self.client.login(username='t', password='pw')
        self.assertContains(self.client.get(reverse('homework:student_dashboard')), self.add_url)

    def test_staff_who_cannot_do_not(self):
        User.objects.create_user('s', password='pw', is_staff=True)
        self.client.login(username='s', password='pw')
        self.assertNotContains(self.client.get(reverse('homework:student_dashboard')), self.add_url)
