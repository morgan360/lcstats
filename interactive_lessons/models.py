# interactive_lessons/models.py
from django.db import models
from django.utils.text import slugify
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


class Question(models.Model):
    """
    Acts as a container or stem for one or more QuestionParts.
    All actual content, answers, and marking live in QuestionPart.
    """
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name="questions")
    order = models.PositiveIntegerField(default=0)
    section = models.CharField(max_length=200, blank=True, null=True)

    # Optional introductory text or image (e.g. for a multi-part question)
    text = models.TextField(blank=True, null=True, help_text="Introductory stem or context for the parts.")
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
        self.text = _maybe_fix(self.text)
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
    answer = models.TextField(blank=True, null=True)
    hint = models.TextField(blank=True, null=True)
    solution = models.TextField(blank=True, null=True)
    order = models.PositiveIntegerField(default=0)

    expected_type = models.CharField(
        max_length=20,
        choices=[
            ("exact", "Exact match"),
            ("numeric", "Numeric"),
            ("expression", "Algebraic Expression"),
            ("multi", "Multiple choice"),
        ],
        default="exact"
    )
    scale = models.CharField(max_length=10, blank=True, null=True)
    max_marks = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("order",)

    def __str__(self):
        return f"{self.question} {self.label or self.order}"
