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
    page_count = models.PositiveSmallIntegerField(
        default=0,
        help_text="Filled in automatically the first time the pages are rendered."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', '-created_at', 'title']
        verbose_name = 'HW Solution'
        verbose_name_plural = 'HW Solutions'

    def __str__(self):
        return self.title


class HWSolutionPage(models.Model):
    """One page of a solutions PDF, rendered to an image.

    Rendered once and kept, because checking a class of 25 against the same
    sheet would otherwise re-render the same PDF 25 times. The images are the
    form the vision model reads -- pulling the text layer out of a maths PDF
    was tried for exam questions and abandoned as too unreliable to build on.

    Public media is the right place for these: the parent PDF is already
    served to students at a public URL from the Downloads menu, so the pages
    disclose nothing the sheet itself does not.
    """
    solution = models.ForeignKey(
        HWSolution,
        on_delete=models.CASCADE,
        related_name='pages',
    )
    page_number = models.PositiveSmallIntegerField()
    image = models.ImageField(upload_to='hw_solutions/pages/')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['solution', 'page_number']
        constraints = [
            models.UniqueConstraint(
                fields=['solution', 'page_number'],
                name='uniq_hwsolutionpage_solution_page',
            )
        ]

    def __str__(self):
        return f"{self.solution.title} — page {self.page_number}"
