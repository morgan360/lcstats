"""The registration-code gate on Google signup.

Social signup goes through a different allauth form than password signup, so
the code requirement does not carry over on its own: without
SOCIALACCOUNT_FORMS pointing at SocialSignupFormWithCode, anyone with a Gmail
account could create an account with no code, no school and no class. These
tests pin that gate shut, and check the code's side effects still fire on the
Google path the way they do on the password one.
"""
from django.contrib.auth.models import User
from django.test import TestCase

from allauth.socialaccount.models import SocialAccount, SocialLogin

from homework.models import TeacherClass, TeacherProfile
from students.forms import SocialSignupFormWithCode
from students.models import RegistrationCode


def sociallogin(email="student@example.com", username="newstudent"):
    """A SocialLogin as allauth hands one to the signup form after Google returns."""
    return SocialLogin(
        user=User(username=username, email=email, first_name="New", last_name="Student"),
        account=SocialAccount(provider="google", uid="google-uid-1", extra_data={}),
    )


def form_for(code, **kwargs):
    login = sociallogin(**kwargs)
    login.email_addresses = []
    data = {
        "username": login.user.username,
        "email": login.user.email,
    }
    if code is not None:
        data["registration_code"] = code
    return SocialSignupFormWithCode(data=data, sociallogin=login)


class GoogleSignupRequiresCodeTests(TestCase):
    def setUp(self):
        self.code = RegistrationCode.objects.create(
            code="STU-TEST-1", code_type="student", max_uses=5
        )

    def test_missing_code_is_rejected(self):
        form = form_for(None)
        self.assertFalse(form.is_valid())
        self.assertIn("registration_code", form.errors)

    def test_unknown_code_is_rejected(self):
        form = form_for("NOT-A-REAL-CODE")
        self.assertFalse(form.is_valid())
        self.assertIn("Invalid registration code.", form.errors["registration_code"])

    def test_inactive_code_is_rejected(self):
        self.code.is_active = False
        self.code.save()
        form = form_for("STU-TEST-1")
        self.assertFalse(form.is_valid())
        self.assertIn("registration_code", form.errors)

    def test_exhausted_code_is_rejected(self):
        self.code.max_uses = 1
        self.code.times_used = 1
        self.code.save()
        form = form_for("STU-TEST-1")
        self.assertFalse(form.is_valid())
        self.assertIn("registration_code", form.errors)

    def test_valid_code_is_accepted(self):
        form = form_for("STU-TEST-1")
        self.assertTrue(form.is_valid(), form.errors)


class GoogleSignupCodeEffectsTests(TestCase):
    """The code does more than gate: it carries school, role and class enrolment."""

    def test_student_code_enrols_into_its_class(self):
        teacher = User.objects.create_user("teacher1", password="x")
        profile = TeacherProfile.objects.create(user=teacher, display_name="T")
        klass = TeacherClass.objects.create(teacher=profile, name="6th Year Maths")
        RegistrationCode.objects.create(
            code="STU-CLASS", code_type="student", teacher_class=klass, max_uses=5
        )

        form = form_for("STU-CLASS")
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save(self._request())

        self.assertIn(user, klass.students.all())

    def test_teacher_code_creates_a_teacher_profile(self):
        RegistrationCode.objects.create(
            code="TCH-TEST", code_type="teacher", max_uses=5
        )

        form = form_for("TCH-TEST", email="teacher@example.com", username="newteacher")
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save(self._request())

        self.assertTrue(TeacherProfile.objects.filter(user=user).exists())

    def test_saving_consumes_a_use_of_the_code(self):
        code = RegistrationCode.objects.create(
            code="STU-ONCE", code_type="student", max_uses=2
        )

        form = form_for("STU-ONCE")
        self.assertTrue(form.is_valid(), form.errors)
        form.save(self._request())

        code.refresh_from_db()
        self.assertEqual(code.times_used, 1)

    def _request(self):
        """A request with a session, which allauth's save_user path expects."""
        from django.contrib.messages.middleware import MessageMiddleware
        from django.contrib.sessions.middleware import SessionMiddleware
        from django.test import RequestFactory

        request = RequestFactory().post("/accounts/social/signup/")
        SessionMiddleware(lambda r: None).process_request(request)
        MessageMiddleware(lambda r: None).process_request(request)
        request.session.save()
        return request
