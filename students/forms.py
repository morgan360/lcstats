from django import forms
from allauth.account.forms import SignupForm
from allauth.socialaccount.forms import SignupForm as SocialSignupForm
from allauth.utils import generate_unique_username
from .models import RegistrationCode


class RegistrationCodeMixin:
    """Shared registration-code handling for the password and Google signup forms.

    The field is added in __init__ rather than declared: Django's form metaclass
    only collects declared fields from bases that are themselves forms, so a
    field set as a plain class attribute here would be silently dropped.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['registration_code'] = forms.CharField(
            max_length=50,
            required=True,
            help_text="Enter your registration code to create an account.",
            widget=forms.TextInput(attrs={
                'placeholder': 'Registration Code',
                'class': 'form-control'
            })
        )

    def clean_registration_code(self):
        code = self.cleaned_data.get('registration_code', '').strip()

        try:
            reg_code = RegistrationCode.objects.get(code=code)
        except RegistrationCode.DoesNotExist:
            raise forms.ValidationError("Invalid registration code.")

        if not reg_code.can_be_used():
            if not reg_code.is_active:
                raise forms.ValidationError("This registration code is no longer active.")
            elif reg_code.is_exhausted():
                raise forms.ValidationError("This registration code has reached its usage limit.")

        # Store the reg_code object for use in save()
        self._reg_code = reg_code
        return code

    def apply_registration_code(self, user):
        """Assign school, role and class enrolment from the validated code."""
        code = self.cleaned_data.get('registration_code')
        if not code or not hasattr(self, '_reg_code'):
            return user

        reg_code = self._reg_code

        # Assign school from registration code to student profile (signal creates StudentProfile)
        if reg_code.school:
            # StudentProfile is created by signal, so we can update it here
            if hasattr(user, 'studentprofile'):
                user.studentprofile.school = reg_code.school
                user.studentprofile.save()

        # Set user permissions based on code type
        if reg_code.code_type == 'teacher':
            # Note: is_staff is NOT set - teachers use Teacher Dashboard, not Django Admin
            # Only superusers (created via createsuperuser) get admin access

            # Create TeacherProfile for teacher users
            from homework.models import TeacherProfile
            teacher_profile, created = TeacherProfile.objects.get_or_create(
                user=user,
                defaults={
                    'display_name': user.get_full_name() or user.username,
                    'email': user.email,
                    'school': reg_code.school  # Assign school from registration code
                }
            )
            # Update school if profile already existed
            if not created and reg_code.school:
                teacher_profile.school = reg_code.school
                teacher_profile.save()
        elif reg_code.code_type == 'student':
            # If code is linked to a class, auto-enroll the student
            if reg_code.teacher_class:
                reg_code.teacher_class.students.add(user)

        # Mark the registration code as used
        reg_code.use_code()

        return user


class SignupFormWithCode(RegistrationCodeMixin, SignupForm):
    """Username/password signup at /accounts/signup/."""

    def save(self, request):
        user = super().save(request)
        return self.apply_registration_code(user)


class SocialSignupFormWithCode(RegistrationCodeMixin, SocialSignupForm):
    """Google signup at /accounts/social/signup/.

    Reached only when SOCIALACCOUNT_AUTO_SIGNUP is off, so a Google account
    cannot be created without a valid code any more than a password one can.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Google supplies email and first/last name but never a username, and
        # allauth only auto-generates one at save time - which this form never
        # reaches, because it stops to ask for a registration code. Left alone
        # the field renders empty and every student has to invent something.
        # Email first: a school address gives a far more recognisable username
        # than a bare first name, and generate_unique_username drops the domain
        # and resolves collisions against existing users.
        if not self.initial.get('username'):
            user = self.sociallogin.user
            full_name = '{}{}'.format(
                user.first_name or '', user.last_name or ''
            ).strip()
            self.initial['username'] = generate_unique_username([
                self.initial.get('email'),
                full_name,
                user.first_name,
                'user',
            ])

    def save(self, request):
        user = super().save(request)
        return self.apply_registration_code(user)
