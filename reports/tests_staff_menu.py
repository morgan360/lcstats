from django.contrib.auth.models import User
from django.test import TestCase

from homework.models import TeacherProfile

ORDER = ['My Classes', 'Student assignments', 'Homework', 'New Homework', 'Study Plans',
         'Homework Check', '>Admin<', 'Site Activity', 'Users', 'Import Flashcards', 'Main Admin']


class StaffMenuTests(TestCase):
    """The staff dropdown is one "Teaching" menu in labelled sections."""

    def _desktop_menu(self, user):
        self.client.force_login(user)
        html = self.client.get('/').content.decode()
        if '<span>Teaching</span>' not in html:
            return None
        start = html.index('<span>Teaching</span>')
        return html[start:html.index('</div>\n                    </div>', start)]

    def test_superuser_sees_every_section_in_order(self):
        boss = User.objects.create_superuser('boss', 'boss@example.com', 'pw')
        TeacherProfile.objects.create(user=boss, display_name='Mr Boss')
        menu = self._desktop_menu(boss)
        positions = [menu.index(label) for label in ORDER]
        self.assertEqual(positions, sorted(positions))
        self.assertNotIn('>Reports<', menu)
        self.assertNotIn('>Teacher<', menu)

    def test_plain_teacher_gets_no_superuser_links_but_keeps_admin_section(self):
        teacher = User.objects.create_user('teach', password='pw', is_staff=True)
        TeacherProfile.objects.create(user=teacher, display_name='Ms Teach')
        menu = self._desktop_menu(teacher)
        for label in ('Site Activity', '>Users<', 'New Homework'):
            self.assertNotIn(label, menu)
        for label in ('>Admin<', 'Import Flashcards', 'Main Admin', 'My Classes'):
            self.assertIn(label, menu)

    def test_student_sees_no_teaching_menu(self):
        student = User.objects.create_user('kid', password='pw')
        self.assertIsNone(self._desktop_menu(student))
        self.assertNotIn('Main Admin', self.client.get('/').content.decode())
