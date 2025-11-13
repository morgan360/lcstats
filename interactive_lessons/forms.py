from django import forms


class QuestionContactForm(forms.Form):
    """Form for students to contact teacher about a specific question"""
    subject = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Brief subject (e.g., "Need help with Q5 part (b)")'
        })
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 6,
            'placeholder': 'Describe your question or issue...'
        })
    )

    def __init__(self, *args, **kwargs):
        self.question = kwargs.pop('question', None)
        self.student = kwargs.pop('student', None)
        super().__init__(*args, **kwargs)