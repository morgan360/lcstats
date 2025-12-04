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

        return code

    def save(self, request):
        # Call parent save to create the user
        user = super(SignupFormWithCode, self).save(request)

        # Mark the registration code as used
        code = self.cleaned_data.get('registration_code')
        if code:
            reg_code = RegistrationCode.objects.get(code=code)
            reg_code.use_code()

        return user
