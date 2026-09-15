"""One student's homework history.

Reports are kept for good, but the list page shows only the latest sixty, so
this page is where older ones stay reachable. It gathers one person's work in
one place for another person's account, so who may see what is tested first.
"""
from datetime import timedelta

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from homework.models import TeacherClass, TeacherProfile
from homework_check.models import HomeworkCheck
from homework_check.views import _count_line
from hw_solutions.models import HWSolution


def make_teacher(username, superuser=False):
    user = User.objects.create_user(username=username, password='pw', is_staff=True,
                                    is_superuser=superuser)
    group, _ = Group.objects.get_or_create(name='Teachers')
    user.groups.add(group)
    return user, TeacherProfile.objects.create(user=user)


class StudentPageTests(TestCase):

    def setUp(self):
        self.teacher, self.profile = make_teacher('t')
        self.other, self.other_profile = make_teacher('other')
        self.student = User.objects.create_user(
            'sam', password='pw', first_name='Sam', last_name='Student')
        self.sixth = TeacherClass.objects.create(teacher=self.profile, name='6th Year')
        self.sixth.students.add(self.student)
        self.solution = HWSolution.objects.create(title='Algebra 2 - Solutions')
        self.url = reverse('homework_check:student_reports', args=[self.student.pk])
        self.client.login(username='t', password='pw')

    def check(self, name, days_ago=0, teacher_class=None, teacher=None, **fields):
        c = HomeworkCheck.objects.create(
            teacher=teacher or self.teacher, teacher_class=teacher_class or self.sixth,
            student=self.student, solution=self.solution, exercise_name=name,
            status=HomeworkCheck.Status.COMPLETE, **fields)
        HomeworkCheck.objects.filter(pk=c.pk).update(
            created_at=timezone.now() - timedelta(days=days_ago))
        return c

    def test_lists_every_report_newest_first(self):
        self.check('Exercise 2.1', days_ago=10)
        self.check('Exercise 2.2, 2.3', days_ago=1)
        response = self.client.get(self.url)
        self.assertContains(response, 'Sam Student')
        self.assertContains(response, '2 homework reports')
        body = response.content.decode()
        self.assertLess(body.index('Exercise 2.2, 2.3'), body.index('Exercise 2.1'))

    def test_more_than_the_list_page_holds(self):
        """The reason the page exists: nothing drops off after sixty."""
        for i in range(65):
            self.check(f'Ex {i}', days_ago=i)
        response = self.client.get(self.url)
        self.assertContains(response, '65 homework reports')
        self.assertContains(response, '>Ex 64<')

    def test_rows_say_how_the_questions_went(self):
        self.check('Ex 1', counts={'total': 12, 'correct': 10, 'slip': 2, 'wrong': 0})
        response = self.client.get(self.url)
        self.assertContains(response, '12 questions: 10 right, 2 slips')

    def test_ratings_are_tallied_with_the_teachers_word_first(self):
        self.check('Ex 1', rating='good')
        self.check('Ex 2', rating='good')
        self.check('Ex 3', rating='fair', teacher_rating='excellent')
        tally = self.client.get(self.url).context['tally']
        self.assertEqual(tally, [('Excellent', 1), ('Good', 2)])

    def test_another_teachers_report_on_the_same_student_is_not_shown(self):
        theirs = TeacherClass.objects.create(teacher=self.other_profile, name='Their class')
        theirs.students.add(self.student)
        self.check('Mine')
        self.check('Theirs', teacher_class=theirs, teacher=self.other)
        response = self.client.get(self.url)
        self.assertContains(response, 'Mine')
        self.assertNotContains(response, 'Theirs')
        self.assertNotContains(response, 'Their class')

    def test_a_student_not_in_your_classes_is_refused(self):
        stranger = User.objects.create_user('stranger', password='pw')
        response = self.client.get(
            reverse('homework_check:student_reports', args=[stranger.pk]))
        self.assertEqual(response.status_code, 403)

    def test_a_student_who_left_the_class_keeps_their_history(self):
        self.check('Before they moved')
        self.sixth.students.remove(self.student)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Before they moved')

    def test_a_student_with_no_reports_gets_the_empty_page(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'No homework has been checked for this student yet.')

    def test_a_superuser_can_look_at_any_student(self):
        make_teacher('admin', superuser=True)
        self.check('Ex 1')
        self.client.login(username='admin', password='pw')
        self.assertContains(self.client.get(self.url), 'Ex 1')

    def test_a_student_cannot_open_it(self):
        self.client.login(username='sam', password='pw')
        response = self.client.get(self.url)
        self.assertNotEqual(response.status_code, 200)

    def test_each_report_links_back_to_the_page(self):
        c = self.check('Ex 1')
        response = self.client.get(reverse('homework_check:check_detail', args=[c.pk]))
        self.assertContains(response, self.url)


class CountLineTests(TestCase):
    def test_wording(self):
        self.assertEqual(_count_line({'total': 12, 'correct': 10, 'slip': 2}),
                         '12 questions: 10 right, 2 slips')
        self.assertEqual(_count_line({'total': 1, 'correct': 0, 'wrong': 1}),
                         '1 question: 0 right, 1 wrong')
        self.assertEqual(
            _count_line({'total': 13, 'correct': 0, 'unclear': 13, 'not_in_solutions': 13}),
            '13 questions: 0 right, 13 not in the solutions')

    def test_nothing_before_marking(self):
        self.assertEqual(_count_line({}), '')
        self.assertEqual(_count_line(None), '')
