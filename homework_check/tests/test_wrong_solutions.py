"""Where a check marked against the wrong solutions is flagged to the teacher.

The rule itself is tested in test_assembly. These make sure the teacher sees
it wherever they would otherwise take the check for finished: the check page,
the lists, and the batch page as each copy completes.
"""
from unittest import mock

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from homework.models import TeacherClass, TeacherProfile
from homework_check.models import CheckPhoto, HomeworkCheck
from hw_solutions.models import HWSolution

MISMATCH = {'total': 13, 'correct': 0, 'unclear': 13, 'not_in_solutions': 13}
FINE = {'total': 12, 'correct': 10, 'slip': 2, 'not_in_solutions': 0}


class WrongSolutionsWarningTests(TestCase):

    def setUp(self):
        self.teacher = User.objects.create_user('t', password='pw', is_staff=True)
        self.teacher.groups.add(Group.objects.get_or_create(name='Teachers')[0])
        profile = TeacherProfile.objects.create(user=self.teacher)
        self.student = User.objects.create_user('s', password='pw')
        self.cls = TeacherClass.objects.create(teacher=profile, name='6th Year')
        self.cls.students.add(self.student)
        self.solution = HWSolution.objects.create(title='Ch 1- Algebra 1 _Solutions')
        self.client.login(username='t', password='pw')

    def check(self, counts, status=HomeworkCheck.Status.COMPLETE):
        return HomeworkCheck.objects.create(
            teacher=self.teacher, teacher_class=self.cls, student=self.student,
            solution=self.solution, exercise_name='Exercise 1.1, 1.2, 1.3',
            solution_pages='2-21', status=status, counts=counts)

    def test_the_check_page_says_what_to_fix(self):
        c = self.check(MISMATCH)
        response = self.client.get(reverse('homework_check:check_detail', args=[c.pk]))
        self.assertContains(response, 'Check the solutions you picked')
        self.assertContains(response, "13 of the 13 questions")
        self.assertContains(response, 'Ch 1- Algebra 1 _Solutions, pages 2-21')

    def test_no_warning_on_an_ordinary_report(self):
        c = self.check(FINE)
        response = self.client.get(reverse('homework_check:check_detail', args=[c.pk]))
        self.assertNotContains(response, 'Check the solutions you picked')

    def test_not_before_marking_has_finished(self):
        c = self.check(MISMATCH, status=HomeworkCheck.Status.ANALYSING)
        self.assertFalse(c.solutions_mismatch)

    def test_the_lists_flag_it_instead_of_no_rating(self):
        self.check(MISMATCH)
        for url in (reverse('homework_check:index'),
                    reverse('homework_check:student_reports', args=[self.student.pk])):
            response = self.client.get(url)
            self.assertContains(response, 'Check solutions')
            self.assertNotContains(response, 'No rating')

    def test_the_batch_page_is_told_when_a_copy_finishes(self):
        c = self.check({}, status=HomeworkCheck.Status.ANALYSING)
        CheckPhoto.objects.create(hw_check=c, order=0, status=CheckPhoto.Status.ANALYSED)

        def finalise(check):
            check.counts = MISMATCH
            check.status = HomeworkCheck.Status.COMPLETE
            check.save()

        with mock.patch('homework_check.services.runner.analyse_next_chunk',
                        return_value=(1, 1)), \
             mock.patch('homework_check.services.runner.finalise', side_effect=finalise):
            body = self.client.post(
                reverse('homework_check:analyse_next', args=[c.pk])).json()
        self.assertTrue(body['complete'])
        self.assertTrue(body['wrong_solutions'])

    def test_an_ordinary_finish_is_not_flagged(self):
        c = self.check({}, status=HomeworkCheck.Status.ANALYSING)
        CheckPhoto.objects.create(hw_check=c, order=0, status=CheckPhoto.Status.ANALYSED)

        def finalise(check):
            check.counts = FINE
            check.status = HomeworkCheck.Status.COMPLETE
            check.save()

        with mock.patch('homework_check.services.runner.analyse_next_chunk',
                        return_value=(1, 1)), \
             mock.patch('homework_check.services.runner.finalise', side_effect=finalise):
            body = self.client.post(
                reverse('homework_check:analyse_next', args=[c.pk])).json()
        self.assertFalse(body['wrong_solutions'])
