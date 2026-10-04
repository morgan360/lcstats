from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from homework.models import TeacherClass, TeacherProfile


class UserListFiltersTests(TestCase):
    """The admin Users list filters by class and by the class's teacher."""

    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser('boss', 'boss@example.com', 'pw')
        t1 = TeacherProfile.objects.create(user=User.objects.create_user('t1'), display_name='Mr One')
        t2 = TeacherProfile.objects.create(user=User.objects.create_user('t2'), display_name='Ms Two')
        cls.sixth = TeacherClass.objects.create(teacher=t1, name='6th')
        cls.fifth = TeacherClass.objects.create(teacher=t1, name='5th')
        other = TeacherClass.objects.create(teacher=t2, name='Other')
        cls.ava = User.objects.create_user('ava')
        cls.both = User.objects.create_user('both')
        cls.elsewhere = User.objects.create_user('elsewhere')
        cls.sixth.students.add(cls.ava, cls.both)
        cls.fifth.students.add(cls.both)
        other.students.add(cls.elsewhere)
        cls.t1 = t1

    def _listed(self, **params):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('admin:auth_user_changelist'), params)
        self.assertEqual(response.status_code, 200)
        return sorted(u.username for u in response.context['cl'].result_list)

    def test_class_filter(self):
        self.assertEqual(self._listed(**{'class': self.sixth.pk}), ['ava', 'both'])

    def test_teacher_filter_lists_each_student_once(self):
        self.assertEqual(self._listed(teacher=self.t1.pk), ['ava', 'both'])

    def test_filters_combine(self):
        self.assertEqual(self._listed(**{'class': self.fifth.pk, 'teacher': self.t1.pk}), ['both'])
