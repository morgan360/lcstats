from django.core.validators import FileExtensionValidator
from django.db import models

from core.models import Subject


class HWSolution(models.Model):
    """
    A homework solution PDF, uploaded by staff and readable by any logged-in
    student from the Downloads menu.
    """
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='hw_solutions',
        null=True,
        blank=True,
        help_text="Subject this belongs to. Leave blank to show it under every subject."
    )
    title = models.CharField(
        max_length=200,
        help_text="Title of the homework solution (e.g. 'Week 3 - Trigonometry')"
    )
    description = models.TextField(
        blank=True,
        help_text="Optional note about what this solution covers"
    )
    pdf_file = models.FileField(
        upload_to='hw_solutions/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])],
        help_text="Upload PDF file"
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order (lower numbers appear first)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', '-created_at', 'title']
        verbose_name = 'HW Solution'
        verbose_name_plural = 'HW Solutions'

    def __str__(self):
        return self.title
