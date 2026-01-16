from django import forms
from allauth.account.forms import SignupForm
from .models import RegistrationCode


class SignupFormWithCode(SignupForm):
    registration_code = forms.CharField(
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

    def save(self, request):
        # Call parent save to create the user
        user = super(SignupFormWithCode, self).save(request)

        # Get the registration code object
        code = self.cleaned_data.get('registration_code')
        if code and hasattr(self, '_reg_code'):
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
