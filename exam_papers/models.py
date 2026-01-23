# exam_papers/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.utils import timezone
from interactive_lessons.models import Topic


class ExamPaper(models.Model):
    """
    Represents a complete Leaving Certificate exam paper.
    Links multiple questions together into a cohesive exam experience.
    """
    PAPER_TYPE_CHOICES = [
        ('p1', 'Paper 1'),
        ('p2', 'Paper 2'),
    ]

    year = models.IntegerField(help_text="Year of the exam (e.g., 2024)")
    paper_type = models.CharField(
        max_length=10,
        choices=PAPER_TYPE_CHOICES,
        help_text="Paper 1 or Paper 2"
    )
    is_deferred = models.BooleanField(
        default=False,
        help_text="Is this a deferred exam paper?"
    )
    title = models.CharField(
        max_length=255,
        help_text="Display title (e.g., 'Leaving Certificate 2024 Paper 1')"
    )
    slug = models.SlugField(unique=True, blank=True)

    # Timing
    time_limit_minutes = models.IntegerField(
        default=150,
        help_text="Total time allowed for this paper in minutes"
    )

    # Marks
    total_marks = models.IntegerField(
        help_text="Total marks available on this paper"
    )

    # Instructions and metadata
    instructions = models.TextField(
        blank=True,
        help_text="General instructions for the paper (e.g., 'Answer 6 out of 8 questions')"
    )

    # PDF reference
    source_pdf = models.FileField(
        upload_to='exam_papers/pdfs/',
        blank=True,
        null=True,
        help_text="Original exam paper PDF"
    )

    # Marking scheme PDF (uploaded separately)
    marking_scheme_pdf = models.FileField(
        upload_to='exam_papers/marking_schemes/pdfs/',
        blank=True,
        null=True,
        help_text="Official marking scheme PDF for this paper"
    )

    # Display options
    is_published = models.BooleanField(
        default=False,
        help_text="Whether this paper is visible to students"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-year', 'paper_type', 'is_deferred']
        unique_together = ('year', 'paper_type', 'is_deferred')

    def __str__(self):
        deferred_suffix = " (Deferred)" if self.is_deferred else ""
        return f"{self.year} {self.get_paper_type_display()}{deferred_suffix}"

    def save(self, *args, **kwargs):
        if not self.slug:
            deferred_suffix = "-deferred" if self.is_deferred else ""
            self.slug = slugify(f"{self.year}-{self.paper_type}{deferred_suffix}")
        if not self.title:
            deferred_text = " Deferred" if self.is_deferred else ""
            self.title = f"Leaving Certificate {self.year}{deferred_text} {self.get_paper_type_display()}"
        super().save(*args, **kwargs)


class ExamQuestion(models.Model):
    """
    Represents a question on an exam paper.
    Can have multiple parts (a), (b), (c), etc.
    """
    exam_paper = models.ForeignKey(
        ExamPaper,
        on_delete=models.CASCADE,
        related_name='questions'
    )

    # Question identification
    question_number = models.PositiveIntegerField(
        help_text="Question number on the paper (e.g., 1, 2, 3)"
    )

    # Topic classification
    topic = models.ForeignKey(
        Topic,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='exam_questions',
        help_text="Topic this question belongs to"
    )

    # Question content
    title = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional title/description of the question"
    )
    image = models.ImageField(
        upload_to='exam_papers/questions/',
        blank=True,
        null=True,
        help_text="Diagram or image for the question stem"
    )

    # Timing (optional per-question timer)
    suggested_time_minutes = models.IntegerField(
        null=True,
        blank=True,
        help_text="Suggested time for this question in minutes"
    )

    # Marks
    total_marks = models.IntegerField(
        help_text="Total marks for this question (sum of all parts)"
    )

    # Display order
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order within the paper"
    )

    class Meta:
        ordering = ['exam_paper', 'order', 'question_number']
        unique_together = ('exam_paper', 'question_number')

    def __str__(self):
        return f"{self.exam_paper} - Q{self.question_number}"


class ExamQuestionPart(models.Model):
    """
    Represents a part of an exam question (e.g., part (a), (b), (c)).
    Uses marking scheme images for GPT-4 Vision-based grading.
    """
    question = models.ForeignKey(
        ExamQuestion,
        on_delete=models.CASCADE,
        related_name='parts'
    )

    # Part identification
    label = models.CharField(
        max_length=10,
        help_text="Part label (e.g., '(a)', '(b)', '(i)', '(ii)')"
    )

    # Marking Scheme (replaces answer/solution fields)
    solution_image = models.ImageField(
        upload_to='exam_papers/marking_schemes/',
        blank=True,
        null=True,
        help_text="Marking scheme image - used by GPT-4 Vision for grading and extracting max marks"
    )

    # Marking (optional - auto-extracted from marking scheme if not set)
    max_marks = models.IntegerField(
        null=True,
        blank=True,
        help_text="Maximum marks for this part (leave blank to auto-extract from marking scheme image)"
    )

    # Solution access control
    solution_unlock_after_attempts = models.PositiveIntegerField(
        default=2,
        help_text="Number of attempts before marking scheme becomes visible (0 = always visible)"
    )

    # Display order
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order within the question"
    )

    class Meta:
        ordering = ['question', 'order']
        unique_together = ('question', 'label')

    def __str__(self):
        return f"{self.question} {self.label}"




class ExamAttempt(models.Model):
    """
    Tracks a student's attempt at an exam paper.
    Can be a full paper attempt or individual question practice.
    """
    ATTEMPT_MODE_CHOICES = [
        ('full_timed', 'Full Paper - Timed'),
        ('full_practice', 'Full Paper - Practice'),
        ('question_practice', 'Individual Question Practice'),
    ]

    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='exam_attempts'
    )
    exam_paper = models.ForeignKey(
        ExamPaper,
        on_delete=models.CASCADE,
        related_name='attempts'
    )

    # Attempt metadata
    attempt_mode = models.CharField(
        max_length=20,
        choices=ATTEMPT_MODE_CHOICES,
        default='question_practice'
    )

    # Timing
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    time_spent_seconds = models.IntegerField(
        default=0,
        help_text="Total time spent on this attempt"
    )

    # Pause/Resume functionality
    is_paused = models.BooleanField(
        default=False,
        help_text="Whether the exam is currently paused"
    )
    paused_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the exam was paused"
    )
    total_paused_seconds = models.IntegerField(
        default=0,
        help_text="Total time the exam has been paused (to calculate accurate time remaining)"
    )

    # Scoring
    total_marks_awarded = models.FloatField(default=0.0)
    total_marks_possible = models.FloatField(default=0.0)
    percentage_score = models.FloatField(default=0.0)

    # Status
    is_completed = models.BooleanField(default=False)
    is_submitted = models.BooleanField(
        default=False,
        help_text="True if student submitted the exam (for timed mode)"
    )

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.student.username} - {self.exam_paper} ({self.started_at.strftime('%Y-%m-%d')})"

    def calculate_score(self):
        """Calculate total score from all question attempts"""
        question_attempts = self.question_attempts.all()
        self.total_marks_awarded = sum(qa.marks_awarded for qa in question_attempts)
        self.total_marks_possible = sum(qa.max_marks for qa in question_attempts)

        if self.total_marks_possible > 0:
            self.percentage_score = (self.total_marks_awarded / self.total_marks_possible) * 100
        else:
            self.percentage_score = 0.0

        self.save()


class ExamQuestionAttempt(models.Model):
    """
    Tracks a student's attempt at a specific exam question part.
    Multiple attempts can exist for practice mode.
    """
    exam_attempt = models.ForeignKey(
        ExamAttempt,
        on_delete=models.CASCADE,
        related_name='question_attempts'
    )
    question_part = models.ForeignKey(
        ExamQuestionPart,
        on_delete=models.CASCADE,
        related_name='attempts'
    )

    # Student's answer
    student_answer = models.TextField(blank=True)

    # Grading
    marks_awarded = models.FloatField(default=0.0)
    max_marks = models.IntegerField()
    is_correct = models.BooleanField(default=False)
    feedback = models.TextField(
        blank=True,
        help_text="Automated or manual feedback"
    )

    # Attempt metadata
    attempt_number = models.PositiveIntegerField(
        default=1,
        help_text="Which attempt is this (1st, 2nd, 3rd, etc.)"
    )
    time_spent_seconds = models.IntegerField(
        default=0,
        help_text="Time spent on this specific question part"
    )

    # Help usage tracking
    hint_used = models.BooleanField(default=False)
    solution_viewed = models.BooleanField(default=False)

    # Timestamps
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-submitted_at']

    def __str__(self):
        return f"{self.exam_attempt.student.username} - {self.question_part} (Attempt {self.attempt_number})"


class ExamQuestionFeedback(models.Model):
    """Track student feedback (thumbs up/down) on exam question grading/feedback."""
    FEEDBACK_CHOICES = [
        ('helpful', 'Thumbs Up'),
        ('not_helpful', 'Thumbs Down'),
    ]

    attempt = models.ForeignKey(
        ExamQuestionAttempt,
        on_delete=models.CASCADE,
        related_name='feedback_responses',
        help_text="The exam question attempt this feedback is for"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='exam_question_feedback',
        help_text="Student who provided feedback"
    )
    feedback_type = models.CharField(
        max_length=20,
        choices=FEEDBACK_CHOICES,
        help_text="Whether student found feedback helpful or not"
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ['attempt', 'user']
        verbose_name = 'Exam Question Feedback'
        verbose_name_plural = 'Exam Question Feedback'

    def __str__(self):
        return f"{self.user.username} - {self.get_feedback_type_display()} - Attempt {self.attempt.id}"