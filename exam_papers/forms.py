"""
Admin forms for exam paper management.
"""
from django import forms
from .models import ExamPaper


class ExtractQuestionsForm(forms.Form):
    """
    Form for extracting questions from an exam paper PDF.
    Provides user-friendly interface for page range specification.
    """
    extraction_method = forms.ChoiceField(
        choices=[
            ('page_ranges', 'Page Ranges (Manual)'),
            ('auto_split', 'Auto Split'),
        ],
        initial='page_ranges',
        widget=forms.RadioSelect,
        help_text='Choose how to extract questions from the PDF'
    )

    page_ranges = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 8,
            'cols': 60,
            'placeholder': 'Enter page ranges for each question:\n1:4-5\n2:6-7\n3:8-9\n4:10-11\n5:12-13\n6:14-15\n7:16-19\n8:20-23\n9:24-27\n10:28-30'
        }),
        help_text='Format: question_number:start_page-end_page (one per line)'
    )

    num_questions = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=20,
        initial=10,
        widget=forms.NumberInput(attrs={'placeholder': '10'}),
        help_text='Number of questions (for auto split method)'
    )

    def clean(self):
        cleaned_data = super().clean()
        method = cleaned_data.get('extraction_method')
        page_ranges = cleaned_data.get('page_ranges')
        num_questions = cleaned_data.get('num_questions')

        if method == 'page_ranges':
            if not page_ranges:
                raise forms.ValidationError('Page ranges are required when using manual extraction method.')

            # Validate page ranges format
            try:
                for line in page_ranges.strip().split('\n'):
                    line = line.strip()
                    if not line:
                        continue
                    if ':' not in line or '-' not in line:
                        raise ValueError(f'Invalid format: {line}')
                    q_num, pages = line.split(':')
                    start, end = pages.split('-')
                    int(q_num)  # Validate it's a number
                    int(start)
                    int(end)
            except ValueError as e:
                raise forms.ValidationError(
                    f'Invalid page range format. Expected "question:start-end". Error: {e}'
                )

        elif method == 'auto_split':
            if not num_questions:
                raise forms.ValidationError('Number of questions is required for auto split method.')

        return cleaned_data

    def get_page_ranges_list(self):
        """
        Parse page ranges into list of tuples.
        Returns: [(question_num, start_page, end_page), ...]
        """
        page_ranges = self.cleaned_data.get('page_ranges', '')
        result = []

        for line in page_ranges.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
            q_num, pages = line.split(':')
            start, end = pages.split('-')
            result.append((int(q_num), int(start), int(end)))

        return result