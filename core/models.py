from django.db import models
from django.utils.text import slugify


class Subject(models.Model):
    """
    Represents a subject in the platform (e.g., Maths, Physics).
    Allows multi-subject support across all content types.
    """
    name = models.CharField(
        max_length=50,
        unique=True,
        help_text="Subject name (e.g., 'Maths', 'Physics')"
    )
    slug = models.SlugField(
        unique=True,
        blank=True,
        help_text="URL-friendly identifier (auto-generated from name)"
    )
    display_order = models.PositiveIntegerField(
        default=0,
        help_text="Order in which subjects appear on homepage (lower = first)"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this subject is available to students"
    )

    # Display settings
    icon = models.CharField(
        max_length=50,
        blank=True,
        help_text="Icon class or emoji for subject (e.g., '📐', '⚡')"
    )
    description = models.TextField(
        blank=True,
        help_text="Brief description shown on subject selection page"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', 'name']
        verbose_name = "Subject"
        verbose_name_plural = "Subjects"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
