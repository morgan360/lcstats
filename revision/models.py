from django.db import models
from django.utils.text import slugify


class RevisionModule(models.Model):
    """Main revision module for a topic"""
    topic = models.OneToOneField(
        'interactive_lessons.Topic',
        on_delete=models.CASCADE,
        related_name='revision_module'
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, help_text="Brief overview of what this revision module covers")
    is_published = models.BooleanField(default=False, help_text="Make visible to students")
    order = models.IntegerField(default=0, help_text="Display order (lower numbers appear first)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'title']
        verbose_name = "Revision Module"
        verbose_name_plural = "Revision Modules"

    def __str__(self):
        return f"{self.title} (Topic: {self.topic.name})"

    @property
    def slug(self):
        """Get the slug from the related topic"""
        return self.topic.slug


class RevisionSection(models.Model):
    """Individual sections within a revision module"""
    module = models.ForeignKey(
        RevisionModule,
        on_delete=models.CASCADE,
        related_name='sections'
    )
    title = models.CharField(max_length=200, help_text="Section heading")
    order = models.IntegerField(default=0, help_text="Display order within the module")

    # Text content
    text_content = models.TextField(
        blank=True,
        help_text="Main content - supports Markdown and LaTeX (use $...$ for inline math, $$...$$ for display math)"
    )

    # Optional image
    image = models.ImageField(
        upload_to='revision/images/',
        blank=True,
        null=True,
        help_text="Optional image for this section"
    )
    image_caption = models.CharField(max_length=200, blank=True)

    # GeoGebra integration
    geogebra_enabled = models.BooleanField(
        default=False,
        help_text="Enable GeoGebra interactive visualization"
    )
    geogebra_material_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="GeoGebra Material ID (e.g., 'abcd1234' from geogebra.org/m/abcd1234)"
    )
    geogebra_width = models.IntegerField(
        default=800,
        help_text="Width in pixels"
    )
    geogebra_height = models.IntegerField(
        default=600,
        help_text="Height in pixels"
    )
    geogebra_show_toolbar = models.BooleanField(
        default=False,
        help_text="Show GeoGebra toolbar to students"
    )
    geogebra_show_menu = models.BooleanField(
        default=False,
        help_text="Show GeoGebra menu bar to students"
    )

    # Video integration
    video_enabled = models.BooleanField(
        default=False,
        help_text="Enable video embed"
    )
    video_url = models.URLField(
        blank=True,
        help_text="YouTube URL (e.g., https://www.youtube.com/watch?v=...) or direct video URL"
    )
    video_caption = models.CharField(max_length=200, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']
        verbose_name = "Revision Section"
        verbose_name_plural = "Revision Sections"

    def __str__(self):
        return f"{self.module.title} - {self.title}"

    @property
    def has_content(self):
        """Check if section has any content"""
        return bool(
            self.text_content or
            self.image or
            (self.geogebra_enabled and self.geogebra_material_id) or
            (self.video_enabled and self.video_url)
        )
