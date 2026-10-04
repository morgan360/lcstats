from django.db import models
from interactive_lessons.models import Topic


class CheatSheet(models.Model):
    """
    A PDF filed under a topic: the topic's Summary Notes, its two-page Cheat
    Sheet, or a reference document such as the Log Tables booklet. Each kind
    has its own page under the Study menu.
    """
    KIND_SUMMARY_NOTES = 'summary_notes'
    KIND_CHEAT_SHEET = 'cheat_sheet'
    KIND_REFERENCE = 'reference'
    KIND_CHOICES = [
        (KIND_SUMMARY_NOTES, 'Summary Notes'),
        (KIND_CHEAT_SHEET, 'Cheat Sheet'),
        (KIND_REFERENCE, 'Reference'),
    ]

    topic = models.ForeignKey(
        Topic,
        on_delete=models.CASCADE,
        related_name='cheatsheets',
        help_text="Topic this cheat sheet belongs to"
    )
    kind = models.CharField(
        max_length=20,
        choices=KIND_CHOICES,
        default=KIND_CHEAT_SHEET,
        db_index=True,
        help_text="Summary Notes and Cheat Sheets are listed on separate pages; "
                  "Reference (the Log Tables booklet) is listed on neither"
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
