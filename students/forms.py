from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import RegistrationCode


class SignupFormWithCode(UserCreationForm):
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
