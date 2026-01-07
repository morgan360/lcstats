from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from markdownx.models import MarkdownxField


class NewsItem(models.Model):
    """News/announcement items displayed on student dashboard"""

    title = models.CharField(max_length=200, help_text="Headline for the news item")
    content = MarkdownxField(help_text="Content with markdown and LaTeX support")

    # Audience targeting
    target_classes = models.ManyToManyField(
        'homework.TeacherClass',
        blank=True,
        related_name='news_items',
        help_text="Leave empty for general announcement to all students. Select classes for targeted announcements."
    )

    # Publishing
    publish_date = models.DateTimeField(
        default=timezone.now,
        help_text="When this item becomes visible"
    )
    expiry_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Optional: when this item should no longer display"
    )

    # Display options
    is_pinned = models.BooleanField(
        default=False,
        help_text="Pinned items appear at the top"
    )
    is_dismissible = models.BooleanField(
        default=True,
        help_text="If False, students cannot dismiss this item (use for critical announcements)"
    )

    # Category/type
    CATEGORY_CHOICES = [
        ('general', 'General'),
        ('new_content', 'New Content'),
        ('tips', 'Study Tips'),
        ('system', 'System Update'),
        ('event', 'Event'),
    ]
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='general'
    )

    # Tracking
    dismissed_by = models.ManyToManyField(
        User,
        blank=True,
        related_name='dismissed_news',
        help_text="Students who have dismissed this item"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_news'
    )

    class Meta:
        ordering = ['-is_pinned', '-publish_date']
        verbose_name = 'News Item'
        verbose_name_plural = 'News Items'

    def __str__(self):
        status = "📌" if self.is_pinned else ""
        return f"{status} {self.title}"

    def is_active(self):
        """Check if news item should be displayed"""
        now = timezone.now()
        if self.publish_date > now:
            return False
        if self.expiry_date and self.expiry_date < now:
            return False
        return True

    def is_dismissed_by(self, user):
        """Check if a specific user has dismissed this item"""
        return self.dismissed_by.filter(id=user.id).exists()

    def is_general(self):
        """Check if this is a general announcement (not class-specific)"""
        return self.target_classes.count() == 0

    def get_target_class_names(self):
        """Get comma-separated list of target class names"""
        classes = self.target_classes.all()
        if not classes:
            return "All Students"
        return ", ".join([c.name for c in classes])

    @classmethod
    def get_active_for_user(cls, user):
        """Get all active news items that haven't been dismissed by the user

        Returns:
        - General announcements (no target_classes)
        - Class-specific announcements if user is enrolled in those classes
        """
        now = timezone.now()
        items = cls.objects.filter(
            publish_date__lte=now
        ).filter(
            models.Q(expiry_date__isnull=True) | models.Q(expiry_date__gt=now)
        )

        # Filter by class membership if user is authenticated
        if user and user.is_authenticated:
            # Show general announcements (no target classes) OR announcements for user's classes
            items = items.filter(
                models.Q(target_classes__isnull=True) |  # General announcements
                models.Q(target_classes__students=user)   # User is in target class
            ).distinct()

            # Exclude dismissed items (only if dismissible)
            items = items.exclude(
                is_dismissible=True,
                dismissed_by=user
            )
        else:
            # Anonymous users only see general announcements
            items = items.filter(target_classes__isnull=True)

        return items
