"""What the pickers offer, and what the analyser refuses to send.

Two faults found in real use on day one, both from the same root: the app was
permissive where it should have been specific. A superuser saw every teacher's
classes in their own dropdown, and an 84-page chapter of solutions could be
sent with every batch of photos.
"""
import shutil
import tempfile
from unittest import mock

from django.contrib.auth.models import Group, User
from django.test import TestCase, override_settings
from django.urls import reverse

from homework.models import TeacherClass, TeacherProfile
from homework_check.models import HomeworkCheck
from homework_check.services import runner
from hw_solutions.models import HWSolution, HWSolutionSection

PRIVATE_ROOT = tempfile.mkdtemp(prefix="hwcheck-scope-test-")


def make_teacher(username, superuser=False):
    user = User.objects.create_user(username=username, password='pw', is_staff=True)
    if superuser:
        user.is_superuser = True
        user.save()
    group, _ = Group.objects.get_or_create(name='Teachers')
    user.groups.add(group)
    return user, TeacherProfile.objects.create(user=user)


@override_settings(PRIVATE_MEDIA_ROOT=PRIVATE_ROOT)
class ClassPickerScopingTests(TestCase):
    """A superuser's own classes, not everyone's.

    Found on the live site: the picker listed three other teachers' classes,
    from other schools, beside the four that were actually mine.
    """

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(PRIVATE_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.admin, self.admin_profile = make_teacher('admin', superuser=True)
        self.other, self.other_profile = make_teacher('other')

        self.mine = TeacherClass.objects.create(
            teacher=self.admin_profile, name='My 6th Year')
        self.theirs = TeacherClass.objects.create(
            teacher=self.other_profile, name='Their 5th Year')
        # Without one of these the page renders its "no solution PDFs yet"
        # branch and the class picker is never drawn at all.
        self.solution = HWSolution.objects.create(title='Ch 1 solutions')
        self.client.login(username='admin', password='pw')

    def test_superuser_picker_shows_only_their_own_classes(self):
        response = self.client.get(reverse('homework_check:check_new'))
        self.assertContains(response, 'My 6th Year')
        self.assertNotContains(response, 'Their 5th Year')

    def test_all_flag_restores_the_full_list(self):
        """An admin supporting a colleague still needs a way through."""
        response = self.client.get(reverse('homework_check:check_new') + '?all=1')
        self.assertContains(response, 'Their 5th Year')

    def test_an_admin_with_no_classes_of_their_own_sees_them_all(self):
        """Otherwise a fresh admin account gets an empty, unusable picker."""
        self.mine.delete()
        response = self.client.get(reverse('homework_check:check_new'))
        self.assertContains(response, 'Their 5th Year')

    def test_an_ordinary_teacher_never_sees_another_teachers_class(self):
        self.client.login(username='other', password='pw')
        response = self.client.get(reverse('homework_check:check_new'))
        self.assertContains(response, 'Their 5th Year')
        self.assertNotContains(response, 'My 6th Year')

    def test_the_list_page_is_scoped_the_same_way(self):
        HomeworkCheck.objects.create(
            teacher=self.other, teacher_class=self.theirs, student=self.other,
            solution=self.solution, exercise_name='Theirs',
        )
        response = self.client.get(reverse('homework_check:index'))
        self.assertNotContains(response, 'Theirs')


@override_settings(PRIVATE_MEDIA_ROOT=PRIVATE_ROOT,
                   HOMEWORK_CHECK_MAX_SOLUTION_PAGES=5)
class SolutionPageGuardTests(TestCase):
    """The solution pages are re-sent with every batch, so the count multiplies."""

    def setUp(self):
        self.teacher, self.profile = make_teacher('t')
        self.student = User.objects.create_user('s', password='pw')
        self.teacher_class = TeacherClass.objects.create(
            teacher=self.profile, name='6th')
        self.teacher_class.students.add(self.student)
        self.solution = HWSolution.objects.create(title='Ch 1', page_count=84)
        self.check = HomeworkCheck.objects.create(
            teacher=self.teacher, teacher_class=self.teacher_class,
            student=self.student, solution=self.solution, exercise_name='Ex 1.1',
        )
        self.client.login(username='t', password='pw')

    @mock.patch('homework_check.services.runner.pages_for_check')
    def test_too_many_pages_is_refused_before_any_call_is_made(self, pages):
        pages.return_value = [mock.Mock() for _ in range(84)]
        with self.assertRaises(runner.TooManySolutionPages):
            runner._encode_solution_pages(self.check)

    @mock.patch('homework_check.services.runner.pages_for_check')
    def test_the_teacher_is_told_the_number_and_what_to_do(self, pages):
        pages.return_value = [mock.Mock() for _ in range(84)]
        try:
            runner._encode_solution_pages(self.check)
        except runner.TooManySolutionPages as e:
            self.assertIn('84', str(e))
            self.assertIn('5', str(e))
            self.assertIn('narrower', str(e))

    @mock.patch('homework_check.services.runner.pages_for_check')
    def test_a_range_within_the_limit_is_allowed_through(self, pages):
        page = mock.Mock()
        page.image.open.return_value.__enter__ = lambda s: s
        page.image.open.return_value.__exit__ = lambda *a: None
        page.page_number = 1
        pages.return_value = [page] * 3
        with mock.patch('homework_check.services.runner.encode_path_for_api',
                        return_value='b64'):
            encoded, numbers = runner._encode_solution_pages(self.check)
        self.assertEqual(len(encoded), 3)

    @mock.patch('homework_check.services.runner.pages_for_check')
    def test_the_check_is_not_marked_failed_when_the_range_is_too_wide(self, pages):
        """It is the teacher's to fix, so the check must stay usable."""
        pages.return_value = [mock.Mock() for _ in range(84)]
        from homework_check.models import CheckPhoto
        CheckPhoto.objects.create(hw_check=self.check, order=0)

        response = self.client.post(
            reverse('homework_check:analyse_next', args=[self.check.pk]))
        body = response.json()
        self.assertFalse(body['success'])
        self.assertIn('84', body['message'])

        self.check.refresh_from_db()
        self.assertNotEqual(self.check.status, HomeworkCheck.Status.FAILED)


class SectionModelTests(TestCase):
    def test_page_range_string_matches_what_the_parser_accepts(self):
        sol = HWSolution.objects.create(title='S')
        multi = HWSolutionSection(solution=sol, label='Exercise 1.3',
                                  first_page=17, last_page=21)
        single = HWSolutionSection(solution=sol, label='Exercise 1.9',
                                   first_page=60, last_page=60)
        self.assertEqual(multi.page_range, '17-21')
        self.assertEqual(multi.page_count, 5)
        self.assertEqual(single.page_range, '60')
        self.assertEqual(single.page_count, 1)

        from homework_check.services.solution_pages import parse_page_range
        self.assertEqual(parse_page_range(multi.page_range, 84),
                         [17, 18, 19, 20, 21])
        self.assertEqual(parse_page_range(single.page_range, 84), [60])


@override_settings(PRIVATE_MEDIA_ROOT=PRIVATE_ROOT)
class CarriedOverSettingsTests(TestCase):
    """"Check another student" brings the last check's settings forward.

    Marking a class is a stack of copies: the class, exercise, solutions PDF
    and page range are the same for all of them and only the student and the
    photographs change. The values arrive as query parameters, which a
    teacher can edit, so each one is re-checked here rather than trusted.
    """

    def setUp(self):
        self.teacher, self.profile = make_teacher('t')
        self.student = User.objects.create_user('s', password='pw')
        self.teacher_class = TeacherClass.objects.create(
            teacher=self.profile, name='6th')
        self.teacher_class.students.add(self.student)
        self.solution = HWSolution.objects.create(title='Ch 1', page_count=84)
        self.other_solution = HWSolution.objects.create(title='Ch 2',
                                                        page_count=40)
        self.client.login(username='t', password='pw')

    def carry(self, **params):
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return self.client.get(f"{reverse('homework_check:check_new')}?{query}")

    def test_the_exercise_name_comes_back_filled_in(self):
        response = self.carry(exercise='Exercise%201.1')
        self.assertContains(response, 'value="Exercise 1.1"')

    def test_the_solutions_pdf_comes_back_selected(self):
        response = self.carry(solution=self.other_solution.pk)
        self.assertContains(
            response, f'value="{self.other_solution.pk}" selected')

    def test_the_page_range_comes_back(self):
        """escapejs writes the hyphen as \\u002D, which is still "2-12" to JS."""
        response = self.carry(solution=self.solution.pk, pages='2-12')
        self.assertContains(response, 'carriedPages = "2\\u002D12"')

    def test_the_class_comes_back_selected(self):
        response = self.carry(**{'class': self.teacher_class.pk,
                                 'exercise': 'Ex+1.1'})
        self.assertContains(response, f'value="{self.teacher_class.pk}" selected')

    def test_a_plain_new_check_carries_nothing(self):
        """The banner and the prefilled name belong only to a repeat."""
        response = self.client.get(reverse('homework_check:check_new'))
        self.assertNotContains(response, 'Same exercise as the last one')
        self.assertContains(response, 'value=""')

    def test_a_solution_that_does_not_exist_is_ignored_not_an_error(self):
        """A hand-edited URL must not 500, and must not select anything."""
        response = self.carry(solution=99999, exercise='Ex+1.1')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '99999')

    def test_a_non_numeric_solution_is_ignored(self):
        response = self.carry(solution='../../etc', exercise='Ex+1.1')
        self.assertEqual(response.status_code, 200)

    def test_a_carried_exercise_name_is_length_capped(self):
        """The field is 200 chars; the URL is not bounded by the form."""
        response = self.carry(exercise='x' * 500)
        self.assertContains(response, 'x' * 200)
        self.assertNotContains(response, 'x' * 201)

    def test_the_repeat_banner_names_the_exercise(self):
        response = self.carry(exercise='Exercise%201.6')
        self.assertContains(response, 'Same exercise as the last one')
        self.assertContains(response, 'Exercise 1.6')

    def test_the_finished_report_offers_the_repeat(self):
        check = HomeworkCheck.objects.create(
            teacher=self.teacher, teacher_class=self.teacher_class,
            student=self.student, solution=self.solution,
            exercise_name='Exercise 1.1', solution_pages='2-12',
            status=HomeworkCheck.Status.COMPLETE,
        )
        response = self.client.get(
            reverse('homework_check:check_detail', args=[check.pk]))
        self.assertContains(response, 'Check another student')
        self.assertContains(response, f'solution={self.solution.pk}')
        self.assertContains(response, 'pages=2-12')
        self.assertContains(response, 'exercise=Exercise%201.1')
