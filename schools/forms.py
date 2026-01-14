"""Forms for school outreach email management."""

from django import forms


class SendEmailForm(forms.Form):
    """Form for composing and sending outreach emails to schools."""

    EMAIL_TYPE_CHOICES = [
        ('initial', 'Initial Outreach'),
        ('follow_up', 'Follow-up'),
        ('reminder', 'Reminder'),
        ('custom', 'Custom'),
    ]

    email_type = forms.ChoiceField(
        choices=EMAIL_TYPE_CHOICES,
        initial='initial',
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text="Select the type of email to send"
    )

    subject = forms.CharField(
        max_length=200,
        initial="Introducing NumScoil - AI-Powered Maths Tutor for Leaving Cert Students",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'size': '80'
        }),
        help_text="Email subject line"
    )

    use_template = forms.BooleanField(
        initial=True,
        required=False,
        help_text="Use the default initial outreach email template"
    )

    custom_message = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 20,
            'cols': 80
        }),
        help_text="Custom email message (only used if 'Use template' is unchecked)"
    )

    prefer_secondary_contact = forms.BooleanField(
        initial=True,
        required=False,
        help_text="Prefer secondary contact (maths teacher/career guidance) over principal when available"
    )

    send_test = forms.BooleanField(
        initial=False,
        required=False,
        help_text="Send test email to yourself instead of schools"
    )