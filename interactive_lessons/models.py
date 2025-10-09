from django.db import models
from markdownx.models import MarkdownxField

from django.utils.text import slugify

class Topic(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name



# interactive_lessons/models.py


# interactive_lessons/models.py
from django.db import models

class Question(models.Model):
    topic = models.ForeignKey("Topic", on_delete=models.CASCADE, related_name="questions")
    order = models.PositiveIntegerField(default=0)
    section = models.CharField(max_length=200, blank=True, null=True)
    text = models.TextField()
    answer = models.TextField(blank=True, null=True)
    hint = models.TextField(blank=True, null=True)
    solution = models.TextField(blank=True, null=True)

    # ✅ Image fields
    image = models.ImageField(
        upload_to="question_images/",
        blank=True,
        null=True,
        help_text="Optional image upload for this question."
    )
    image_url = models.URLField(
        blank=True,
        null=True,
        help_text="Alternatively, provide an external image URL."
    )

    def __str__(self):
        return f"{self.topic.name} - Q{self.order}"

    def get_image(self):
        """Return image file if uploaded, else image_url."""
        if self.image:
            return self.image.url
        return self.image_url
