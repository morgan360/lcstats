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

        # 1. Try to get from parent_assignment kwarg (Django admin inline context)
        if parent_assignment and hasattr(parent_assignment, 'topic'):
            topic = parent_assignment.topic
        # 2. Check if editing existing task
        elif self.instance and self.instance.assignment_id:
            try:
                assignment = self.instance.assignment
                if assignment and assignment.topic:
                    topic = assignment.topic
            except:
                pass
        # 3. Check POST data for assignment (form submission)
        elif self.data.get('assignment'):
            try:
                from homework.models import HomeworkAssignment
                assignment = HomeworkAssignment.objects.get(pk=self.data['assignment'])
                if assignment and assignment.topic:
                    topic = assignment.topic
            except (ValueError, HomeworkAssignment.DoesNotExist):
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
            self.fields['section'].help_text = "Save assignment first to see filtered options"

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
            self.fields['exam_question'].help_text = "Save assignment first to see filtered options"

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
            self.fields['quickkick'].help_text = "Save assignment first to see filtered options"

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
            self.fields['flashcard_set'].help_text = "Save assignment first to see filtered options"

    def clean(self):
        cleaned_data = super().clean()

        # Validate that flashcard_set is selected
        if not cleaned_data.get('flashcard_set'):
            raise forms.ValidationError("Please select a Flashcard Set")

        # Ensure task_type is set (already set in __init__, but confirm in cleaned_data)
        cleaned_data['task_type'] = 'flashcard'

        return cleaned_data