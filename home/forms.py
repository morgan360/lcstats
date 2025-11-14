from django import forms


class ContactForm(forms.Form):
    """Form for general contact inquiries"""
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your name',
            'style': 'width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 4px; font-size: 1em; box-sizing: border-box;'
        })
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'your.email@example.com',
            'style': 'width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 4px; font-size: 1em; box-sizing: border-box;'
        })
    )
    subject = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Subject of your message',
            'style': 'width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 4px; font-size: 1em; box-sizing: border-box;'
        })
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 6,
            'placeholder': 'Your message...',
            'style': 'width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 4px; font-size: 1em; box-sizing: border-box; resize: vertical;'
        })
    )
