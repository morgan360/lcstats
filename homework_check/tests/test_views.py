"""The flow: privacy, ownership, and what a teacher is told on failure.

The load-bearing tests are the privacy invariant -- photographs of a named
child's work must never land where the web server publishes them -- and the
failure path, where an exception must never reach the page as text.

Ownership is tested as hard, because unlike the student-facing work photos,
this feature exposes one person's work to another person's account. A teacher
reaching another teacher's class would be the worst bug here.
"""
import io
import shutil
import tempfile
from unittest import mock

from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from homework.models import TeacherClass, TeacherProfile
from homework_check.models import CheckPhoto, HomeworkCheck
from hw_solutions.models import HWSolution

PRIVATE_ROOT = tempfile.mkdtemp(prefix="hwcheck-private-test-")

CANNED = {
    "readable": True, "confidence": "high", "has_diagram": False,
    "diagram_feedback": "",
    "questions": [
        {"label": "1", "found_in_solutions": True, "student_answer": "$x=4$",
         "correct_answer": "$x=4$", "verdict": "correct",
         "comment": "Correct.", "continues": False},
        {"label": "2", "found_in_solutions": True, "student_answer": "$x=-3$",
         "correct_answer": "$x=3$", "verdict": "slip",
         "comment": "Sign slip on the last line.", "continues": False},
        {"label": "3", "found_in_solutions": True, "student_answer": "$7$",
         "correct_answer": "$9$", "verdict": "correct",
         "comment": "Fine.", "continues": False},
    ],
    "notes": "",
    "model_used": "test-model",
    "usage": {"prompt_tokens": 10, "completion_tokens": 5},
}


def photo(name="page.jpg", size=(1200, 1600)):
    buffer = io.BytesIO()
    Image.new("RGB", size, "white").save(buffer, format="JPEG")
    return SimpleUploadedFile(name, buffer.getvalue(), "image/jpeg")


def make_teacher(username):
    user = User.objects.create_user(username=username, password='pw', is_staff=True)
    group, _ = Group.objects.get_or_create(name='Teachers')
    user.groups.add(group)
    return user, TeacherProfile.objects.create(user=user)


@override_settings(PRIVATE_MEDIA_ROOT=PRIVATE_ROOT)
class HomeworkCheckFlowTests(TestCase):

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(PRIVATE_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.teacher, self.profile = make_teacher('teacher_a')
        self.other_teacher, self.other_profile = make_teacher('teacher_b')

        self.student = User.objects.create_user('aoife', password='pw',
                                                first_name='Aoife')
        self.teacher_class = TeacherClass.objects.create(
            teacher=self.profile, name='6th Year HL')
        self.teacher_class.students.add(self.student)

        self.solution = HWSolution.objects.create(
            title='Ex 5A solutions', page_count=2)

        self.check = HomeworkCheck.objects.create(
            teacher=self.teacher, teacher_class=self.teacher_class,
            student=self.student, solution=self.solution,
            exercise_name='Ex 5A',
        )
        self.client.login(username='teacher_a', password='pw')

    def upload(self):
        return self.client.post(
            reverse('homework_check:check_upload', args=[self.check.pk]),
            {'photo': photo()},
        )

    # -- privacy ----------------------------------------------------------

    def test_photo_is_stored_outside_the_published_media_directory(self):
        """The invariant this feature was built around.

        On PythonAnywhere /media/ is a static mapping served outside Django,
        so anything there is readable by anyone who guesses the URL. These are
        photographs of a named child's work.
        """
        self.assertTrue(self.upload().json()['success'])
        stored = CheckPhoto.objects.get().image.path
        self.assertIn(PRIVATE_ROOT, stored)

    def test_the_stored_file_has_no_public_url(self):
        self.upload()
        with self.assertRaises(ValueError):
            CheckPhoto.objects.get().image.url

    def test_photo_is_served_to_the_owning_teacher(self):
        self.upload()
        photo_row = CheckPhoto.objects.get()
        response = self.client.get(
            reverse('homework_check:check_photo', args=[photo_row.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Cache-Control'], 'private, no-store')

    def test_photo_is_not_served_to_another_teacher(self):
        self.upload()
        photo_row = CheckPhoto.objects.get()
        self.client.login(username='teacher_b', password='pw')
        response = self.client.get(
            reverse('homework_check:check_photo', args=[photo_row.pk]))
        self.assertEqual(response.status_code, 403)

    def test_deleting_a_photo_removes_the_file(self):
        """'Delete' has to actually delete, or the retention promise is empty."""
        self.upload()
        row = CheckPhoto.objects.get()
        path = row.image.path
        import os
        self.assertTrue(os.path.exists(path))
        self.client.post(reverse('homework_check:photo_delete', args=[row.pk]))
        self.assertFalse(os.path.exists(path))

    # -- ownership --------------------------------------------------------

    def test_another_teacher_cannot_open_the_check(self):
        self.client.login(username='teacher_b', password='pw')
        response = self.client.get(
            reverse('homework_check:check_detail', args=[self.check.pk]))
        self.assertEqual(response.status_code, 403)

    def test_another_teacher_cannot_edit_the_report(self):
        self.client.login(username='teacher_b', password='pw')
        response = self.client.post(
            reverse('homework_check:check_edit', args=[self.check.pk]),
            data='{"field": "summary", "value": "hacked"}',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 403)
        self.check.refresh_from_db()
        self.assertEqual(self.check.summary, '')

    def test_another_teacher_cannot_print_the_report(self):
        self.client.login(username='teacher_b', password='pw')
        response = self.client.get(
            reverse('homework_check:report_print', args=[self.check.pk]))
        self.assertEqual(response.status_code, 403)

    def test_a_student_cannot_reach_any_of_it(self):
        self.client.login(username='aoife', password='pw')
        for name in ('check_detail', 'report_print'):
            with self.subTest(view=name):
                response = self.client.get(
                    reverse(f'homework_check:{name}', args=[self.check.pk]))
                self.assertEqual(response.status_code, 403)

    def test_a_teacher_only_sees_their_own_checks_in_the_list(self):
        other_class = TeacherClass.objects.create(
            teacher=self.other_profile, name='5th Year')
        HomeworkCheck.objects.create(
            teacher=self.other_teacher, teacher_class=other_class,
            student=self.student, solution=self.solution,
            exercise_name='Not mine',
        )
        response = self.client.get(reverse('homework_check:index'))
        self.assertContains(response, 'Ex 5A')
        self.assertNotContains(response, 'Not mine')

    # -- limits -----------------------------------------------------------

    @override_settings(HOMEWORK_CHECK_MAX_PHOTOS=2)
    def test_photo_limit_is_enforced_on_the_endpoint_not_just_the_page(self):
        self.assertTrue(self.upload().json()['success'])
        self.assertTrue(self.upload().json()['success'])
        third = self.upload().json()
        self.assertFalse(third['success'])
        self.assertIn('limit', third['message'])
        self.assertEqual(CheckPhoto.objects.count(), 2)

    def test_a_file_that_is_not_an_image_is_refused_with_a_readable_message(self):
        response = self.client.post(
            reverse('homework_check:check_upload', args=[self.check.pk]),
            {'photo': SimpleUploadedFile('notes.txt', b'not an image', 'image/jpeg')},
        )
        body = response.json()
        self.assertFalse(body['success'])
        self.assertIn("doesn't look like a photo", body['message'])

    # -- analysis ---------------------------------------------------------

    @mock.patch('homework_check.services.runner.summarise')
    @mock.patch('homework_check.services.runner.analyse_chunk')
    @mock.patch('homework_check.services.runner._encode_solution_pages')
    def test_a_full_run_produces_a_report(self, pages, analyse, summary):
        pages.return_value = ([], [])
        analyse.return_value = dict(CANNED)
        summary.return_value = ("Work on your signs.", {"prompt_tokens": 1,
                                                        "completion_tokens": 1})
        self.upload()

        response = self.client.post(
            reverse('homework_check:analyse_next', args=[self.check.pk]))
        body = response.json()
        self.assertTrue(body['success'])
        self.assertTrue(body['complete'])

        self.check.refresh_from_db()
        self.assertEqual(self.check.status, HomeworkCheck.Status.COMPLETE)
        self.assertEqual(len(self.check.findings), 3)
        # 2 correct + 1 slip over 3 = 2.5/3 = 0.83 -> good
        self.assertEqual(self.check.rating, 'good')
        self.assertEqual(self.check.summary, 'Work on your signs.')

    @mock.patch('homework_check.services.runner._encode_solution_pages')
    def test_an_analysis_failure_never_reaches_the_teacher_as_text(self, pages):
        """The deliberate break from the older graders, which leak str(e).

        The detail belongs in the log and the error_message column, not on a
        page -- it is noise at best and a leak at worst.
        """
        pages.side_effect = RuntimeError("boom: sk-secret-key-in-the-message")
        self.upload()

        with self.assertLogs('homework_check.views', level='ERROR'):
            response = self.client.post(
                reverse('homework_check:analyse_next', args=[self.check.pk]))

        body = response.json()
        self.assertFalse(body['success'])
        self.assertNotIn('sk-secret', body['message'])
        self.assertNotIn('boom', body['message'])

        self.check.refresh_from_db()
        self.assertEqual(self.check.status, HomeworkCheck.Status.FAILED)
        self.assertIn('boom', self.check.error_message)

    @mock.patch('homework_check.services.runner.summarise')
    @mock.patch('homework_check.services.runner.analyse_chunk')
    @mock.patch('homework_check.services.runner._encode_solution_pages')
    @override_settings(HOMEWORK_CHECK_CHUNK_SIZE=2)
    def test_photos_are_analysed_in_chunks_not_all_at_once(self, pages, analyse, summary):
        """Sixteen photos in one call would run past the vision timeout."""
        pages.return_value = ([], [])
        analyse.return_value = dict(CANNED)
        summary.return_value = ("ok", {"prompt_tokens": 1, "completion_tokens": 1})
        for _ in range(5):
            self.upload()

        calls = 0
        while True:
            body = self.client.post(
                reverse('homework_check:analyse_next', args=[self.check.pk])).json()
            calls += 1
            if body['complete'] or calls > 10:
                break

        self.assertEqual(calls, 3)          # 2 + 2 + 1
        self.assertEqual(analyse.call_count, 3)
        for call in analyse.call_args_list:
            self.assertLessEqual(len(call.args[0]), 2)

    # -- editing ----------------------------------------------------------

    def test_the_teachers_rating_wins_over_the_computed_one(self):
        self.check.rating = 'poor'
        self.check.save()
        self.client.post(
            reverse('homework_check:check_edit', args=[self.check.pk]),
            data='{"field": "rating", "value": "good"}',
            content_type='application/json',
        )
        self.check.refresh_from_db()
        self.assertEqual(self.check.rating, 'poor')
        self.assertEqual(self.check.final_rating, 'good')

    def test_an_unknown_rating_is_refused(self):
        response = self.client.post(
            reverse('homework_check:check_edit', args=[self.check.pk]),
            data='{"field": "rating", "value": "brilliant"}',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        self.check.refresh_from_db()
        self.assertEqual(self.check.teacher_rating, '')

    def test_editing_a_question_comment_changes_only_that_one(self):
        self.check.findings = [
            {'label': '1', 'comment': 'first', 'verdict': 'correct',
             'student_answer': '', 'correct_answer': '', 'found_in_solutions': True,
             'continues': False},
            {'label': '2', 'comment': 'second', 'verdict': 'wrong',
             'student_answer': '', 'correct_answer': '', 'found_in_solutions': True,
             'continues': False},
        ]
        self.check.save()

        self.client.post(
            reverse('homework_check:check_edit', args=[self.check.pk]),
            data='{"field": "comment", "label": "2", "value": "reworded"}',
            content_type='application/json',
        )
        self.check.refresh_from_db()
        self.assertEqual(self.check.findings[0]['comment'], 'first')
        self.assertEqual(self.check.findings[1]['comment'], 'reworded')

    def test_editing_marks_the_check_reviewed(self):
        """So an unreviewed report is never mistaken for a checked one."""
        self.assertIsNone(self.check.reviewed_at)
        self.client.post(
            reverse('homework_check:check_edit', args=[self.check.pk]),
            data='{"field": "summary", "value": "Reworded."}',
            content_type='application/json',
        )
        self.check.refresh_from_db()
        self.assertIsNotNone(self.check.reviewed_at)

    def test_a_question_can_be_dropped_from_the_sheet(self):
        self.check.findings = [{'label': '1', 'comment': 'x', 'verdict': 'correct',
                                'student_answer': '', 'correct_answer': '',
                                'found_in_solutions': True, 'continues': False}]
        self.check.save()
        self.client.post(
            reverse('homework_check:check_edit', args=[self.check.pk]),
            data='{"field": "drop_question", "label": "1", "value": ""}',
            content_type='application/json',
        )
        self.check.refresh_from_db()
        self.assertEqual(self.check.findings, [])

    # -- the printed sheet -------------------------------------------------

    def test_the_report_shows_the_correct_answers(self):
        """The deliberate inversion: this sheet is handed to the student."""
        self.check.findings = [
            {'label': '2', 'comment': 'Sign slip.', 'verdict': 'slip',
             'student_answer': '$x=-3$', 'correct_answer': '$x=3$',
             'found_in_solutions': True, 'continues': False},
        ]
        self.check.summary = 'Watch your signs.'
        self.check.save()

        response = self.client.get(
            reverse('homework_check:report_print', args=[self.check.pk]))
        self.assertContains(response, 'Sign slip.')
        self.assertContains(response, 'Watch your signs.')
        self.assertContains(response, 'Aoife')

    def test_the_report_does_not_extend_the_site_shell(self):
        """No nav, no dark theme -- it is a sheet of paper."""
        response = self.client.get(
            reverse('homework_check:report_print', args=[self.check.pk]))
        self.assertNotContains(response, 'navMenu')
