"""The upload flow: privacy, token scope, and what a student is told on failure.

The load-bearing tests here are the privacy invariant (photos must never land
where the web server publishes them) and the failure path (an exception must
never reach the student as text).
"""
import io
import re
import shutil
import tempfile
from unittest import mock

from django.conf import settings
from django.contrib.auth.models import User
from django.core import signing
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from exam_papers.models import ExamAttempt, ExamPaper, ExamQuestion, ExamQuestionPart
from interactive_lessons.models import Question, QuestionPart, Topic
from students.models import StudentProfile, WorkSubmission
from students.views_work import TOKEN_SALT

PRIVATE_ROOT = tempfile.mkdtemp(prefix="private-media-test-")

CANNED = {
    "readable": True, "has_working": True, "confidence": "high",
    "transcription": "f'(x) = -2 - 6x", "has_diagram": False,
    "steps": [{"step": "Differentiated", "verdict": "correct", "comment": "Right."}],
    "method_feedback": "Sound method.", "diagram_feedback": "",
    "next_step": "Check the last line.", "strengths": ["Clear working"],
    "model_used": "test-model", "usage": {"prompt_tokens": 10, "completion_tokens": 5},
}


def photo(name="working.jpg", size=(1200, 900)):
    buffer = io.BytesIO()
    Image.new("RGB", size, "white").save(buffer, format="JPEG")
    return SimpleUploadedFile(name, buffer.getvalue(), "image/jpeg")


@override_settings(PRIVATE_MEDIA_ROOT=PRIVATE_ROOT, WORK_PHOTO_STAFF_ONLY=False)
class WorkFlowTests(TestCase):
    """The flow itself, with the staff-only trial gate off.

    The gate is covered separately in StaffOnlyGateTests.
    """

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(PRIVATE_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.user = User.objects.create_user("aoife", password="pw")
        self.other = User.objects.create_user("cian", password="pw")
        self.student = StudentProfile.objects.get(user=self.user)

        topic = Topic.objects.create(name="Calculus", slug="calculus")
        question = Question.objects.create(topic=topic)
        self.part = QuestionPart.objects.create(
            question=question, label="(a)", prompt="Find $f'(10)$.", answer="-62"
        )

    # -- slot ------------------------------------------------------------
    def open_slot(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("work_slot"), {"part_type": "lesson", "part_id": self.part.pk}
        )
        return response.json()

    def test_slot_returns_a_qr_and_an_awaiting_row(self):
        data = self.open_slot()
        self.assertTrue(data["success"])
        self.assertTrue(data["qr"].startswith("data:image/png;base64,"))
        submission = WorkSubmission.objects.get(pk=data["id"])
        self.assertEqual(submission.status, WorkSubmission.Status.AWAITING_PHOTO)
        self.assertFalse(submission.image)

    def test_slot_requires_login(self):
        response = self.client.post(reverse("work_slot"), {"part_type": "lesson", "part_id": 1})
        self.assertIn(response.status_code, (302, 403))

    @override_settings(WORK_PHOTO_HOURLY_LIMIT=1)
    def test_hourly_limit_applies(self):
        self.open_slot()
        self.assertFalse(self.open_slot()["success"])

    # -- upload ----------------------------------------------------------
    def upload(self, token=None, file=None):
        token = token or signing.dumps({"sub": self.open_slot()["id"]}, salt=TOKEN_SALT)
        return self.client.post(
            reverse("work_mobile_upload", args=[token]), {"photo": file or photo()}
        )

    @mock.patch("students.views_work.analyse_student_work", return_value=dict(CANNED))
    def test_photo_is_stored_privately_and_never_under_media_root(self, _):
        data = self.upload().json()
        self.assertTrue(data["success"], data)
        submission = WorkSubmission.objects.get(pk=data["photo_url"].split("/")[3])
        path = submission.image.path

        # The invariant the whole storage design exists for.
        self.assertTrue(path.startswith(PRIVATE_ROOT), path)
        self.assertFalse(path.startswith(str(settings.MEDIA_ROOT)), path)

    @mock.patch("students.views_work.analyse_student_work", return_value=dict(CANNED))
    def test_upload_needs_no_login_on_the_phone(self, _):
        submission_id = self.open_slot()["id"]
        self.client.logout()
        token = signing.dumps({"sub": submission_id}, salt=TOKEN_SALT)
        self.assertTrue(self.upload(token=token).json()["success"])

    @mock.patch("students.views_work.analyse_student_work", return_value=dict(CANNED))
    def test_analysis_is_flattened_onto_the_row(self, _):
        data = self.upload().json()
        submission = WorkSubmission.objects.get(pk=data["photo_url"].split("/")[3])
        self.assertEqual(submission.status, WorkSubmission.Status.COMPLETE)
        self.assertEqual(submission.transcription, CANNED["transcription"])
        self.assertEqual(submission.next_step, CANNED["next_step"])
        self.assertEqual(submission.prompt_tokens, 10)
        self.assertIsNotNone(submission.analysed_at)

    @mock.patch("students.views_work.analyse_student_work")
    def test_a_failed_analysis_never_shows_the_student_the_exception(self, analyse):
        secret = "OpenAI key sk-abc123 rejected at line 42"
        analyse.side_effect = RuntimeError(secret)

        data = self.upload().json()
        self.assertFalse(data["success"])
        self.assertNotIn(secret, data["message"])
        self.assertNotIn("RuntimeError", data["message"])

        submission = WorkSubmission.objects.latest("created_at")
        self.assertEqual(submission.status, WorkSubmission.Status.FAILED)
        # Kept, but only where an admin can see it.
        self.assertIn(secret, submission.error_message)

    def test_a_bad_photo_is_refused_before_any_api_call(self):
        with mock.patch("students.views_work.analyse_student_work") as analyse:
            bad = SimpleUploadedFile("x.jpg", b"not a jpeg", "image/jpeg")
            data = self.upload(file=bad).json()
            self.assertFalse(data["success"])
            analyse.assert_not_called()

    # -- token scope -----------------------------------------------------
    def test_expired_token_is_refused(self):
        token = signing.dumps({"sub": self.open_slot()["id"]}, salt=TOKEN_SALT)
        with override_settings(WORK_UPLOAD_TOKEN_MAX_AGE=-1):
            response = self.client.post(reverse("work_mobile_upload", args=[token]),
                                        {"photo": photo()})
        self.assertFalse(response.json()["success"])

    def test_tampered_token_is_refused(self):
        response = self.client.post(reverse("work_mobile_upload", args=["forged"]),
                                    {"photo": photo()})
        self.assertFalse(response.json()["success"])

    @mock.patch("students.views_work.analyse_student_work", return_value=dict(CANNED))
    def test_token_is_good_for_one_photo_only(self, _):
        token = signing.dumps({"sub": self.open_slot()["id"]}, salt=TOKEN_SALT)
        self.assertTrue(self.upload(token=token).json()["success"])
        self.assertFalse(self.upload(token=token).json()["success"])

    # -- serving and deletion --------------------------------------------
    @mock.patch("students.views_work.analyse_student_work", return_value=dict(CANNED))
    def test_photo_is_served_to_its_owner_and_nobody_else(self, _):
        submission = WorkSubmission.objects.get(
            pk=self.upload().json()["photo_url"].split("/")[3]
        )
        url = reverse("work_photo", args=[submission.pk])

        self.client.force_login(self.user)
        self.assertEqual(self.client.get(url).status_code, 200)

        self.client.force_login(self.other)
        self.assertEqual(self.client.get(url).status_code, 403)

        self.client.logout()
        self.assertIn(self.client.get(url).status_code, (302, 403))

    @mock.patch("students.views_work.analyse_student_work", return_value=dict(CANNED))
    def test_delete_removes_the_row_and_the_file(self, _):
        submission = WorkSubmission.objects.get(
            pk=self.upload().json()["photo_url"].split("/")[3]
        )
        path = submission.image.path
        import os
        self.assertTrue(os.path.exists(path))

        self.client.force_login(self.user)
        self.client.post(reverse("work_delete", args=[submission.pk]))

        self.assertFalse(WorkSubmission.objects.filter(pk=submission.pk).exists())
        self.assertFalse(os.path.exists(path), "file left behind after delete")

    @mock.patch("students.views_work.analyse_student_work", return_value=dict(CANNED))
    def test_another_student_cannot_delete_your_photo(self, _):
        submission = WorkSubmission.objects.get(
            pk=self.upload().json()["photo_url"].split("/")[3]
        )
        self.client.force_login(self.other)
        response = self.client.post(reverse("work_delete", args=[submission.pk]))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(WorkSubmission.objects.filter(pk=submission.pk).exists())

    # -- no marks --------------------------------------------------------
    @mock.patch("students.views_work.analyse_student_work", return_value=dict(CANNED))
    def test_nothing_is_ever_scored(self, _):
        before = self.student.total_score
        self.upload()
        self.student.refresh_from_db()
        self.assertEqual(self.student.total_score, before)
        self.assertEqual(self.student.attempts.count(), 0)


@override_settings(PRIVATE_MEDIA_ROOT=PRIVATE_ROOT, WORK_PHOTO_STAFF_ONLY=False)
class ExamPartTests(TestCase):
    """The other target type.

    A WorkSubmission points at either a QuestionPart or an ExamQuestionPart,
    and until the exam surface was wired up only the first was ever exercised.
    These cover the second: that the branch binds the right FK, and that an
    exam part reaches the model with its marking scheme as a rubric -- which is
    the whole reason exam feedback should read better than lesson feedback.
    """

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(PRIVATE_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.user = User.objects.create_user("niamh", password="pw")
        self.student = StudentProfile.objects.get(user=self.user)
        self.paper = ExamPaper.objects.create(
            year=2023, paper_type="paper1", title="2023 Paper 1", total_marks=300
        )
        self.question = ExamQuestion.objects.create(
            exam_paper=self.paper, question_number=4, total_marks=25, order=1
        )
        # A second question so the first is not the last one -- see the CSRF
        # test below, which depends on that distinction.
        ExamQuestion.objects.create(
            exam_paper=self.paper, question_number=5, total_marks=25, order=2
        )
        self.part = ExamQuestionPart.objects.create(question=self.question, label="(b)")

    def open_slot(self):
        self.client.force_login(self.user)
        return self.client.post(
            reverse("work_slot"), {"part_type": "exam", "part_id": self.part.pk}
        ).json()

    def test_slot_binds_the_exam_part_and_not_the_lesson_one(self):
        submission = WorkSubmission.objects.get(pk=self.open_slot()["id"])
        self.assertEqual(submission.exam_question_part_id, self.part.pk)
        self.assertIsNone(submission.question_part_id)

    @mock.patch("students.views_work.analyse_student_work", return_value=dict(CANNED))
    def test_exam_part_is_analysed_without_leaking_an_answer(self, analyse):
        token = signing.dumps({"sub": self.open_slot()["id"]}, salt=TOKEN_SALT)
        response = self.client.post(
            reverse("work_mobile_upload", args=[token]), {"photo": photo()}
        )
        self.assertTrue(response.json()["success"], response.json())

        # Exam parts carry no question text -- it exists only as an image -- and
        # no stored answer, so nothing should be handed to the model as one.
        kwargs = analyse.call_args.kwargs
        self.assertIsNone(kwargs["expected_answer"])
        self.assertEqual(kwargs["part_label"], "(b)")

    def test_the_exam_page_renders_a_capture_block_that_can_actually_post(self):
        """The block must carry its own CSRF token.

        Deliberately requests a question that is NOT the last one. The exam
        template only emits {% csrf_token %} inside its "Finish Exam" form,
        which renders on the last question alone -- so on any other question
        the DOM lookup in work_capture.js finds nothing, and without the
        data-csrf attribute every slot POST would come back 403.
        """
        # ExamAttempt.student is the User, unlike WorkSubmission.student.
        attempt = ExamAttempt.objects.create(student=self.user, exam_paper=self.paper)
        self.client.force_login(self.user)
        response = self.client.get(
            reverse("exam_papers:question_interface", args=[attempt.id, self.question.id])
        )
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()

        self.assertIn('data-part-type="exam"', html)
        self.assertIn(f'data-part-id="{self.part.pk}"', html)
        self.assertNotIn("csrfmiddlewaretoken", html)   # the trap this guards

        token = re.search(r'data-csrf="([^"]*)"', html)
        self.assertTrue(token and token.group(1), "capture block carries no CSRF token")

    def test_an_unknown_part_type_is_refused(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("work_slot"), {"part_type": "quickkick", "part_id": self.part.pk}
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(WorkSubmission.objects.count(), 0)


@override_settings(PRIVATE_MEDIA_ROOT=PRIVATE_ROOT, WORK_PHOTO_STAFF_ONLY=True)
class StaffOnlyGateTests(TestCase):
    """While the feature is trialled, only staff can open a slot.

    Checked in the view, not just the template: hiding a button is not access
    control, and this endpoint spends money on a vision call.
    """

    def setUp(self):
        self.student = User.objects.create_user("student", password="pw")
        self.staff = User.objects.create_user("teacher", password="pw", is_staff=True)
        topic = Topic.objects.create(name="Calculus", slug="calculus-gate")
        question = Question.objects.create(topic=topic)
        self.part = QuestionPart.objects.create(question=question, prompt="Find $x$.")

    def open_slot(self, user):
        self.client.force_login(user)
        return self.client.post(
            reverse("work_slot"), {"part_type": "lesson", "part_id": self.part.pk}
        )

    def test_student_is_refused_while_staff_only(self):
        self.assertEqual(self.open_slot(self.student).status_code, 403)

    def test_staff_may_open_a_slot(self):
        self.assertTrue(self.open_slot(self.staff).json()["success"])

    @override_settings(WORK_PHOTO_STAFF_ONLY=False)
    def test_students_allowed_once_the_flag_is_off(self):
        self.assertTrue(self.open_slot(self.student).json()["success"])
