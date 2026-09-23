"""The "Find a student" box in the admin header (templates/admin/base_site.html)."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class AdminStudentSearchTests(TestCase):

    def setUp(self):
        User.objects.create_superuser('admin', 'a@example.com', 'pw')
        User.objects.create_user('cpulcini', first_name='Caterina', last_name='Pulcini')
        User.objects.create_user('fnagni', first_name='Francesco', last_name='Nagni')
        self.client.login(username='admin', password='pw')
        self.changelist = reverse('admin:students_studentprofile_changelist')

    def test_it_is_on_every_admin_page_not_just_the_index(self):
        for url in (reverse('admin:index'), reverse('admin:auth_user_changelist')):
            response = self.client.get(url)
            self.assertContains(response, 'id="ns-student-search"')
            self.assertContains(response, f'action="{self.changelist}"')

    def test_it_finds_a_student_by_surname(self):
        response = self.client.get(self.changelist, {'q': 'pulcini'})
        self.assertContains(response, 'cpulcini')
        self.assertNotContains(response, 'fnagni')

    def test_staff_without_student_permission_do_not_get_it(self):
        User.objects.create_user('staff', password='pw', is_staff=True)
        self.client.login(username='staff', password='pw')
        response = self.client.get(reverse('admin:index'))
        self.assertNotContains(response, 'ns-student-search')
