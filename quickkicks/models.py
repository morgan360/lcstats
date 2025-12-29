from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.utils import timezone
from interactive_lessons.models import Topic, QuestionPart


class QuickKick(models.Model):
    """
    Short animation video (from Manim) or GeoGebra applet linked to a topic.
    Replaces the Revision column in interactive lessons.
    """
    CONTENT_TYPE_CHOICES = [
        ('video', 'Video (MP4)'),
        ('geogebra', 'GeoGebra Applet'),
    ]

    title = models.CharField(max_length=200, help_text="Display title for the resource")
    description = models.TextField(blank=True, help_text="Brief description of what this resource covers")
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name="quickkicks")
    content_type = models.CharField(
        max_length=20,
        choices=CONTENT_TYPE_CHOICES,
        default='video',
        help_text="Type of content: Video or GeoGebra applet"
    )

    # For videos
    video = models.FileField(
        upload_to='quickkicks/',
        blank=True,
        null=True,
        help_text="Upload MP4 video file (required if content type is Video)"
    )
    duration_seconds = models.PositiveIntegerField(
        default=0,
        blank=True,
        help_text="Video duration in seconds (optional, only for videos)"
    )

    # For GeoGebra applets
    geogebra_code = models.CharField(
        max_length=50,
        blank=True,
        help_text="GeoGebra applet code (e.g., 'pvvcyzts') - required if content type is GeoGebra"
    )

    # Optional test question after video
    question_part = models.ForeignKey(
        QuestionPart,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='quickkicks',
        help_text='Optional question to test comprehension after watching (links to existing QuestionPart)'
    )

    order = models.PositiveIntegerField(default=0, help_text="Display order within topic")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('topic', 'order', 'title')
        verbose_name = "QuickKick"
        verbose_name_plural = "QuickKicks"

    def __str__(self):
        content_label = "Video" if self.content_type == 'video' else "GeoGebra"
        return f"{self.topic.name} - {self.title} ({content_label})"

    def clean(self):
        """Validate that either video or geogebra_code is provided based on content_type"""
        if self.content_type == 'video' and not self.video:
            raise ValidationError({'video': 'Video file is required when content type is Video.'})
        if self.content_type == 'geogebra' and not self.geogebra_code:
            raise ValidationError({'geogebra_code': 'GeoGebra code is required when content type is GeoGebra.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def geogebra_embed_url(self):
        """Generate the full GeoGebra embed URL from the code"""
        if self.geogebra_code:
            return f"https://www.geogebra.org/material/iframe/id/{self.geogebra_code}/width/1200/height/600/border/888888/sfsb/true/smb/false/stb/false/stbh/false/ai/false/asb/false/sri/false/rc/false/ld/false/sdz/false/ctl/false"
        return ""


class QuickKickView(models.Model):
    """
    Tracks when students view QuickKicks and their answers to test questions.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quickkick_views')
    quickkick = models.ForeignKey(QuickKick, on_delete=models.CASCADE, related_name='views')
    viewed_at = models.DateTimeField(default=timezone.now)

    # Test question answer tracking
    answer_submitted = models.BooleanField(
        default=False,
        help_text='Whether student has submitted an answer to the test question'
    )
    answer_correct = models.BooleanField(
        default=False,
        help_text='Whether the submitted answer was correct'
    )
    score_awarded = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text='Score awarded (0-100) for the test question'
    )
    attempts = models.PositiveIntegerField(
        default=0,
        help_text='Number of attempts at the test question'
    )
    last_attempt_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the last answer attempt was made'
    )

    class Meta:
        unique_together = ('user', 'quickkick')
        ordering = ['-viewed_at']
        verbose_name = "QuickKick View"
        verbose_name_plural = "QuickKick Views"

    def __str__(self):
        return f"{self.user.username} viewed {self.quickkick.title}"
