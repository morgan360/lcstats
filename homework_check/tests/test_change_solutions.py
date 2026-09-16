"""Pointing an existing check at different solutions.

Written after a real stall: an emailed scan was assigned against Exercise 2.6,
whose solutions run to 37 pages -- over the limit -- so the check could not be
marked, and nothing in the app could change its page range. The scan was gone,
because a scan becomes the check.
"""
from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from homework.models import TeacherClass, TeacherProfile
from homework_check.models import CheckPhoto, HomeworkCheck
from hw_solutions.models import HWSolution


class ChangeSolutionsTests(TestCase):

    def setUp(self):
        self.teacher = User.objects.create_user('t', password='pw', is_staff=True)
        self.teacher.groups.add(Group.objects.get_or_create(name='Teachers')[0])
        profile = TeacherProfile.objects.create(user=self.teacher)
        student = User.objects.create_user('s')
        cls = TeacherClass.objects.create(teacher=profile, name='6th Year')
        cls.students.add(student)
        self.wrong = HWSolution.objects.create(title='Algebra 1')
        self.right = HWSolution.objects.create(title='Algebra 2')
        self.check = HomeworkCheck.objects.create(
            teacher=self.teacher, teacher_class=cls, student=student,
            solution=self.wrong, exercise_name='Exercise 2.6',
            solution_pages='58-94', status=HomeworkCheck.Status.COMPLETE,
            findings=[{'label': '1', 'verdict': 'wrong'}], counts={'total': 1},
            rating='poor', summary='old', analysis=[{'questions': []}],
            teacher_note='my note', teacher_rating='good')
        self.photo = CheckPhoto.objects.create(
            hw_check=self.check, order=0, status=CheckPhoto.Status.ANALYSED)
        self.url = reverse('homework_check:check_solutions', args=[self.check.pk])
        self.client.login(username='t', password='pw')

    def post(self, **fields):
        data = {'solution': self.right.pk, 'solution_pages': '56-58,60-70'}
        data.update(fields)
        return self.client.post(self.url, data)

    def test_it_repoints_the_check_and_clears_the_old_report(self):
        self.post()
        self.check.refresh_from_db()
        self.assertEqual(self.check.solution, self.right)
        self.assertEqual(self.check.solution_pages, '56-58,60-70')
        self.assertEqual((self.check.findings, self.check.counts, self.check.analysis),
                         ([], {}, []))
        self.assertEqual((self.check.rating, self.check.summary), ('', ''))
        self.assertEqual(self.check.status, HomeworkCheck.Status.DRAFT)

    def test_the_photos_are_read_again(self):
        """The whole point: "Check again" alone rebuilds from the old batches."""
        self.post()
        self.photo.refresh_from_db()
        self.assertEqual(self.photo.status, CheckPhoto.Status.PENDING)

    def test_the_teachers_own_words_are_kept(self):
        self.post()
        self.check.refresh_from_db()
        self.assertEqual((self.check.teacher_note, self.check.teacher_rating),
                         ('my note', 'good'))

    def test_the_exercise_can_be_renamed_at_the_same_time(self):
        self.post(exercise_name='HW-B1-2.5')
        self.check.refresh_from_db()
        self.assertEqual(self.check.exercise_name, 'HW-B1-2.5')

    def test_a_blank_name_keeps_the_old_one(self):
        self.post(exercise_name='')
        self.check.refresh_from_db()
        self.assertEqual(self.check.exercise_name, 'Exercise 2.6')

    def test_it_refuses_once_the_photos_are_gone(self):
        self.check.photos_deleted_at = timezone.now()
        self.check.save(update_fields=['photos_deleted_at'])
        self.post()
        self.check.refresh_from_db()
        self.assertEqual(self.check.solution, self.wrong)

    def test_another_teacher_cannot_repoint_it(self):
        other = User.objects.create_user('other', password='pw', is_staff=True)
        other.groups.add(Group.objects.get_or_create(name='Teachers')[0])
        TeacherProfile.objects.create(user=other)
        self.client.login(username='other', password='pw')
        self.assertEqual(self.post().status_code, 403)
        self.check.refresh_from_db()
        self.assertEqual(self.check.solution, self.wrong)

    def test_the_form_is_on_the_check_page_set_to_its_current_solutions(self):
        response = self.client.get(
            reverse('homework_check:check_detail', args=[self.check.pk]))
        self.assertContains(response, 'Change the solutions or pages')
        self.assertContains(response, f'value="{self.wrong.pk}" selected')
        self.assertContains(response, 'carriedPages = "58\\u002D94"')
