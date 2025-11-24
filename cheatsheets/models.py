from django.db import models
from interactive_lessons.models import Topic


class CheatSheet(models.Model):
    """
    Stores PDF cheat sheets organized by topic.
    Each cheat sheet is a PDF file that can be viewed in a separate tab.
    """
    topic = models.ForeignKey(
        Topic,
        on_delete=models.CASCADE,
        related_name='cheatsheets',
        help_text="Topic this cheat sheet belongs to"
    )
    title = models.CharField(
        max_length=200,
        help_text="Title of the cheat sheet"
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Optional description of what's covered in this cheat sheet"
    )
    pdf_file = models.FileField(
        upload_to='cheatsheets/',
        help_text="Upload PDF file"
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order (lower numbers appear first)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['topic__name', 'order', 'title']
        verbose_name = 'Cheat Sheet'
        verbose_name_plural = 'Cheat Sheets'

    def __str__(self):
        return f"{self.topic.name} - {self.title}"
