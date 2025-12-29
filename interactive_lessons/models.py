# interactive_lessons/models.py
from django.db import models
from django.utils.text import slugify
from django.contrib.auth.models import User
from interactive_lessons.utils.katex_sanitizer import sanitize_katex


class Topic(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ("name",)


class Section(models.Model):
    """
    Represents a section within a topic (e.g., 'Sine Rule' within 'Trigonometry').
    All questions must belong to a section for better organization and navigation.
    """
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name="sections")
    order = models.PositiveIntegerField(default=0)

    def save(self, *args, **kwargs):
        if not self.slug:
            # Create slug from topic name + section name to ensure uniqueness
            base_slug = slugify(f"{self.topic.name}-{self.name}")
            self.slug = base_slug
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.topic.name} - {self.name}"

    class Meta:
        ordering = ("topic", "order")
        unique_together = ("topic", "name")


class Question(models.Model):
    """
    Acts as a container or stem for one or more QuestionParts.
    All actual content, answers, and marking live in QuestionPart.
    """
    PAPER_TYPE_CHOICES = [
        ('p1', 'Paper 1'),
        ('p2', 'Paper 2'),
    ]

    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name="questions")
    order = models.PositiveIntegerField(default=0)
    section_old = models.CharField(max_length=200, blank=True, null=True, help_text="DEPRECATED: Old text-based section field")
    section = models.ForeignKey(Section, on_delete=models.PROTECT, related_name="questions", null=True, blank=True)

    # Optional introductory text or image (e.g. for a multi-part question)
    hint = models.TextField(blank=True, null=True, help_text="Hint for this question (applies to all parts).")
    image = models.ImageField(
        upload_to="question_images/",
        blank=True,
        null=True,
        help_text="Optional image upload for this question.",
    )
    image_url = models.URLField(blank=True, null=True)

    # ✅ New full-question solution fields
    solution = models.TextField(blank=True, null=True, help_text="Full worked solution for this question.")
    solution_image = models.ImageField(upload_to="solutions/", blank=True, null=True)

    # ✅ Copyright and source metadata
    is_copyrighted = models.BooleanField(
        default=False,
        help_text="True if this question is copyrighted (e.g., from published exam papers)"
    )

    # ✅ Exam paper metadata (DEPRECATED - exam questions now in separate app)
    is_exam_question = models.BooleanField(
        default=False,
        help_text="DEPRECATED: Use exam_papers app instead. True if this is from an actual LC exam paper"
    )
    exam_year = models.IntegerField(
        null=True,
        blank=True,
        help_text="DEPRECATED: Use exam_papers app instead. Year of the exam (e.g., 2024, 2023)"
    )
    paper_type = models.CharField(
        max_length=10,
        choices=PAPER_TYPE_CHOICES,
        blank=True,
        null=True,
        help_text="DEPRECATED: Use exam_papers app instead. Paper 1 or Paper 2"
    )
    source_pdf_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="DEPRECATED: Use exam_papers app instead. Original PDF filename for reference"
    )

    # QuickKick integration
    is_quickkick_suitable = models.BooleanField(
        default=False,
        help_text="Mark this question as suitable for QuickKick videos (shows in dropdown when adding test questions)"
    )

    def __str__(self):
        return f"{self.topic.name} - Q{self.order}"

    def get_image(self):
        return self.image.url if self.image else self.image_url

    class Meta:
        ordering = ("topic__name", "order")

    def save(self, *args, **kwargs):
        def _maybe_fix(val):
            if val and ("(\\" in val or "[\\" in val):
                return sanitize_katex(val)
            return val
        self.hint = _maybe_fix(self.hint)
        super().save(*args, **kwargs)

    def get_next_id(self):
        next_obj = (
            self.__class__.objects.filter(topic=self.topic, order__gt=self.order)
            .order_by("order")
            .first()
        )
        return next_obj.id if next_obj else None

    def get_prev_id(self):
        prev_obj = (
            self.__class__.objects.filter(topic=self.topic, order__lt=self.order)
            .order_by("-order")
            .first()
        )
        return prev_obj.id if prev_obj else None


class QuestionPart(models.Model):
    """
    Each QuestionPart is an actual sub-question, such as (a), (b), etc.
    All answers, hints, and marking logic belong here.
    """
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="parts"
    )
    label = models.CharField(
        max_length=10,
        blank=True,
        help_text="Label for this part, e.g. (a), (b), (c)"
    )
    prompt = models.TextField(help_text="Text for this part of the question.")
    image = models.ImageField(
        upload_to="question_part_images/",
        blank=True,
        null=True,
        help_text="Optional image for this specific question part (e.g., diagram, graph)."
    )
    answer = models.TextField(blank=True, null=True)
    answer_format_template = models.ForeignKey(
        'exam_papers.AnswerFormatTemplate',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Select a predefined answer format template"
    )
    expected_format = models.TextField(blank=True, null=True, help_text="Custom format description (or leave blank to use template)")
    solution = models.TextField(blank=True, null=True)
    solution_image = models.ImageField(
        upload_to="solutions/",
        blank=True,
        null=True,
        help_text="Optional solution image for this part (e.g., worked solution diagram)"
    )
    order = models.PositiveIntegerField(default=0)

    expected_type = models.CharField(
        max_length=20,
        choices=[
            ("exact", "Exact match"),
            ("numeric", "Numeric"),
            ("expression", "Algebraic Expression"),
            ("multi", "Multiple choice"),
            ("manual", "Manual grading required"),
        ],
        default="exact"
    )

    # QuickKick integration
    is_quickkick_suitable = models.BooleanField(
        default=False,
        help_text="Mark this question as suitable for QuickKick videos (shows in dropdown when adding test questions)"
    )
    scale = models.CharField(max_length=10, blank=True, null=True)
    max_marks = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("order",)

    def __str__(self):
        return f"{self.question} {self.label or self.order}"

    def get_expected_format_display(self):
        """
        Returns the format instruction to show to students.
        Uses template if selected, otherwise returns custom text.
        """
        if self.answer_format_template:
            return self.answer_format_template.description
        return self.expected_format or ""


class StudentInquiry(models.Model):
    """
    Stores student inquiries/messages sent to teachers, along with teacher replies.
    Allows teachers to respond to student questions through the admin interface.
    """
    STATUS_CHOICES = [
        ('unanswered', 'Unanswered'),
        ('answered', 'Answered'),
    ]

    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='inquiries',
        help_text="Student who sent this inquiry"
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inquiries',
        help_text="Question this inquiry is about (if any)"
    )
    subject = models.CharField(max_length=200, help_text="Subject of the inquiry")
    message = models.TextField(help_text="Student's message")

    # Metadata from the original question context
    topic_name = models.CharField(max_length=200, blank=True, null=True)
    question_number = models.CharField(max_length=50, blank=True, null=True)
    section_name = models.CharField(max_length=200, blank=True, null=True)

    # Teacher reply fields
    reply = models.TextField(
        blank=True,
        null=True,
        help_text="Teacher's reply to this inquiry"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='unanswered',
        help_text="Whether this inquiry has been answered"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    replied_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Student Inquiry'
        verbose_name_plural = 'Student Inquiries'

    def __str__(self):
        return f"{self.student.username} - {self.subject} ({self.status})"
