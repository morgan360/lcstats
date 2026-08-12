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


class PasswordSignupStillWorksTests(TestCase):
    """The password signup form shares its code handling with the Google one.

    Both draw the registration_code field and its side effects from
    RegistrationCodeMixin, so a change made for the Google path can break
    password signup without touching its code. This walks the real view.
    """

    def test_password_signup_creates_an_account_and_uses_the_code(self):
        code = RegistrationCode.objects.create(
            code="STU-PASSWORD", code_type="student", max_uses=5
        )
        response = self.client.post(
            "/accounts/signup/",
            {
                "username": "pwstudent",
                "email": "pwstudent@example.com",
                "password1": "sufficiently-long-pw-42",
                "password2": "sufficiently-long-pw-42",
                "registration_code": "STU-PASSWORD",
            },
        )
        self.assertIn(response.status_code, (200, 302))
        user = User.objects.filter(username="pwstudent").first()
        self.assertIsNotNone(user, "password signup did not create the user")
        self.assertTrue(user.has_usable_password())

        code.refresh_from_db()
        self.assertEqual(code.times_used, 1)

    def test_password_signup_is_rejected_without_a_code(self):
        self.client.post(
            "/accounts/signup/",
            {
                "username": "nocode",
                "email": "nocode@example.com",
                "password1": "sufficiently-long-pw-42",
                "password2": "sufficiently-long-pw-42",
            },
        )
        self.assertFalse(User.objects.filter(username="nocode").exists())


class GoogleDoesNotCreateASecondAccountTests(TestCase):
    """Signing in with Google on an existing account must not fork it.

    SOCIALACCOUNT_EMAIL_AUTHENTICATION connects the Google identity to the
    account that already owns that email instead of starting a new signup.
    Note the deliberate side effect: allauth wipes the password when the
    existing email was never verified, to lock out anyone who might have
    pre-registered with someone else's address.
    """

    def test_existing_email_is_connected_not_duplicated(self):
        from allauth.account.models import EmailAddress
        from allauth.socialaccount.internal.flows.email_authentication import (
            wipe_password,
        )

        existing = User.objects.create_user(
            "existing", email="existing@example.com", password="original-password"
        )
        EmailAddress.objects.create(
            user=existing, email="existing@example.com", verified=False, primary=True
        )
        before = User.objects.count()

        # The connect step allauth performs once it matches the email.
        wipe_password(None, existing, "existing@example.com")
        SocialAccount.objects.create(
            user=existing, provider="google", uid="google-existing"
        )

        self.assertEqual(User.objects.count(), before, "a second account was created")
        self.assertEqual(SocialAccount.objects.get(uid="google-existing").user, existing)

        existing.refresh_from_db()
        self.assertFalse(
            existing.has_usable_password(),
            "unverified email should have its password wiped on connect",
        )

    def test_verified_email_keeps_its_password(self):
        from allauth.account.models import EmailAddress
        from allauth.socialaccount.internal.flows.email_authentication import (
            wipe_password,
        )

        user = User.objects.create_user(
            "verified", email="verified@example.com", password="original-password"
        )
        EmailAddress.objects.create(
            user=user, email="verified@example.com", verified=True, primary=True
        )

        wipe_password(None, user, "verified@example.com")

        user.refresh_from_db()
        self.assertTrue(user.has_usable_password())


class GoogleSignupUsernameSuggestionTests(TestCase):
    """Google never sends a username, so the form suggests one.

    allauth only auto-generates a username inside save_user(), which this flow
    never reaches unprompted - it stops at the registration-code form first.
    Without a suggestion the field renders empty for every student.
    """

    def unbound(self, email="morganmcknight@rosarycollege.ie", first="Morgan", last="McKnight"):
        login = sociallogin(email=email, username="")
        login.user.first_name = first
        login.user.last_name = last
        login.email_addresses = []
        return SocialSignupFormWithCode(sociallogin=login)

    def test_username_is_suggested_from_the_email_local_part(self):
        form = self.unbound()
        self.assertEqual(form.initial["username"], "morganmcknight")

    def test_suggestion_never_contains_the_domain(self):
        form = self.unbound()
        self.assertNotIn("@", form.initial["username"])
        self.assertNotIn("rosarycollege", form.initial["username"].replace("morganmcknight", ""))

    def test_suggestion_avoids_an_existing_username(self):
        User.objects.create_user("morganmcknight", password="x")
        form = self.unbound()
        self.assertNotEqual(form.initial["username"], "morganmcknight")
        self.assertTrue(form.initial["username"].startswith("morganmcknight"))

    def test_falls_back_to_the_name_when_email_is_unusable(self):
        form = self.unbound(email="")
        self.assertEqual(form.initial["username"], "morganmcknight")

    def test_suggestion_does_not_override_what_the_student_typed(self):
        login = sociallogin(email="morganmcknight@rosarycollege.ie", username="")
        login.email_addresses = []
        form = SocialSignupFormWithCode(
            data={
                "username": "chosen_by_hand",
                "email": "morganmcknight@rosarycollege.ie",
                "registration_code": "STU-PREFILL",
            },
            sociallogin=login,
        )
        RegistrationCode.objects.create(
            code="STU-PREFILL", code_type="student", max_uses=5
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["username"], "chosen_by_hand")
