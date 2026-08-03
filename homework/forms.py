from django import forms
from .models import HomeworkTask
from interactive_lessons.models import Section
from exam_papers.models import ExamQuestion
from quickkicks.models import QuickKick
from flashcards.models import FlashcardSet


class ExamQuestionChoiceField(forms.ModelChoiceField):
    """Custom choice field to display exam questions with subject"""
    def label_from_instance(self, obj):
        subject = obj.exam_paper.subject.name if obj.exam_paper and obj.exam_paper.subject else "No Subject"
        year = obj.exam_paper.year if obj.exam_paper else "Unknown"
        topic = obj.topic.name if obj.topic else "No Topic"
        return f"[{subject}] {year} - Q{obj.question_number} - {topic}"


# Base form class with common functionality
class BaseHomeworkTaskForm(forms.ModelForm):
    """Base form for homework tasks with topic filtering"""

    class Meta:
        model = HomeworkTask
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        # Extract parent_assignment from kwargs (passed by formset)
        parent_assignment = kwargs.pop('parent_assignment', None)

        super().__init__(*args, **kwargs)

        # Hide task_type field - it will be auto-set by specific form
        if 'task_type' in self.fields:
            self.fields['task_type'].widget = forms.HiddenInput()

        # Get topic from assignment
        topic = None

        # 1. Submitted parent form data — wins so a brand-new assignment (or a
        #    topic change) filters and validates in a single save
        if self.data and self.data.get('topic'):
            try:
                from interactive_lessons.models import Topic
                topic = Topic.objects.get(pk=self.data['topic'])
            except (ValueError, Topic.DoesNotExist):
                pass
        # 2. Parent assignment instance (GET on an existing assignment)
        elif parent_assignment is not None and getattr(parent_assignment, 'topic', None):
            topic = parent_assignment.topic
        # 3. Existing task's own assignment
        elif self.instance and self.instance.assignment_id:
            try:
                assignment = self.instance.assignment
                if assignment and assignment.topic:
                    topic = assignment.topic
            except Exception:
                pass

        # Store topic for use by subclasses
        self.topic = topic


class PracticeQuestionsTaskForm(BaseHomeworkTaskForm):
    """Form for Practice Questions tasks"""

    class Meta:
        model = HomeworkTask
        fields = ['assignment', 'task_type', 'section', 'is_required', 'order']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Auto-set task_type for this inline
        self.instance.task_type = 'section'

        # Filter sections by topic
        if self.topic:
            self.fields['section'].queryset = Section.objects.filter(topic=self.topic)
            self.fields['section'].help_text = f"Practice questions for {self.topic.name}"
        else:
            self.fields['section'].help_text = "Select a topic above to filter these options"

    def clean(self):
        cleaned_data = super().clean()

        # Validate that section is selected
        if not cleaned_data.get('section'):
            raise forms.ValidationError("Please select a Practice Questions section")

        # Ensure task_type is set (already set in __init__, but confirm in cleaned_data)
        cleaned_data['task_type'] = 'section'

        return cleaned_data


class ExamQuestionsTaskForm(BaseHomeworkTaskForm):
    """Form for Exam Questions tasks"""

    # Override the exam_question field to use custom display
    exam_question = ExamQuestionChoiceField(
        queryset=ExamQuestion.objects.all(),
        required=False
    )

    class Meta:
        model = HomeworkTask
        fields = ['assignment', 'task_type', 'exam_question', 'is_required', 'order']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Auto-set task_type for this inline
        self.instance.task_type = 'exam_question'

        # Filter exam questions by topic
        if self.topic:
            self.fields['exam_question'].queryset = ExamQuestion.objects.filter(topic=self.topic)
            self.fields['exam_question'].help_text = f"Exam questions for {self.topic.name}"
        else:
            self.fields['exam_question'].help_text = "Select a topic above to filter these options"

    def clean(self):
        cleaned_data = super().clean()

        # Validate that exam_question is selected
        if not cleaned_data.get('exam_question'):
            raise forms.ValidationError("Please select an Exam Question")

        # Ensure task_type is set (already set in __init__, but confirm in cleaned_data)
        cleaned_data['task_type'] = 'exam_question'

        return cleaned_data


class QuickKicksTaskForm(BaseHomeworkTaskForm):
    """Form for QuickKicks tasks"""

    class Meta:
        model = HomeworkTask
        fields = ['assignment', 'task_type', 'quickkick', 'is_required', 'order']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Auto-set task_type for this inline
        self.instance.task_type = 'quickkick'

        # Filter quickkicks by topic
        if self.topic:
            self.fields['quickkick'].queryset = QuickKick.objects.filter(topic=self.topic)
            self.fields['quickkick'].help_text = f"QuickKicks for {self.topic.name}"
        else:
            self.fields['quickkick'].help_text = "Select a topic above to filter these options"

    def clean(self):
        cleaned_data = super().clean()

        # Validate that quickkick is selected
        if not cleaned_data.get('quickkick'):
            raise forms.ValidationError("Please select a QuickKick")

        # Ensure task_type is set (already set in __init__, but confirm in cleaned_data)
        cleaned_data['task_type'] = 'quickkick'

        return cleaned_data


class FlashcardsTaskForm(BaseHomeworkTaskForm):
    """Form for Flashcards tasks"""

    class Meta:
        model = HomeworkTask
        fields = ['assignment', 'task_type', 'flashcard_set', 'is_required', 'order']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Auto-set task_type for this inline
        self.instance.task_type = 'flashcard'

        # Filter flashcard sets by topic
        if self.topic:
            self.fields['flashcard_set'].queryset = FlashcardSet.objects.filter(topic=self.topic)
            self.fields['flashcard_set'].help_text = f"Flashcard sets for {self.topic.name}"
        else:
            self.fields['flashcard_set'].help_text = "Select a topic above to filter these options"

    def clean(self):
        cleaned_data = super().clean()

        # Validate that flashcard_set is selected
        if not cleaned_data.get('flashcard_set'):
            raise forms.ValidationError("Please select a Flashcard Set")

        # Ensure task_type is set (already set in __init__, but confirm in cleaned_data)
        cleaned_data['task_type'] = 'flashcard'

        return cleaned_data

class CustomTaskForm(BaseHomeworkTaskForm):
    """Form for free-text written exercises, e.g. 'Maths 2 pg 56 Q1 - Q12'"""

    class Meta:
        model = HomeworkTask
        fields = ['assignment', 'task_type', 'instructions', 'is_required']
        widgets = {
            'instructions': forms.TextInput(attrs={'size': 60, 'placeholder': 'e.g. Maths 2 pg 56 Q1 - Q12'}),
        }
        labels = {
            'instructions': 'Exercise',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.task_type = 'custom'
        self.fields['instructions'].help_text = "Textbook exercise, worksheet, or anything else done outside NumScoil"

    def clean(self):
        cleaned_data = super().clean()

        if not (cleaned_data.get('instructions') or '').strip():
            raise forms.ValidationError("Please enter the exercise text")

        cleaned_data['task_type'] = 'custom'

        return cleaned_data
