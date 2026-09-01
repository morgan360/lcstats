"""One student's exercise, photographed and checked against a solutions PDF.

Deliberately not built on ``students.WorkSubmission``. That model belongs to a
StudentProfile, carries a CHECK constraint requiring exactly one of two
question-part foreign keys, and holds per-step commentary on a single
question. This is owned by a teacher, spans up to sixteen photos and many
questions, and has no question part at all. The *services* are shared --
private storage, image intake, the vision wrapper -- but the row is not.
"""
import uuid
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from students.storage import private_storage


def check_photo_path(instance, filename):
    """Per-check directory, random filename.

    The filename is not the security boundary -- these are served by a view
    that checks the teacher owns the class -- but there is no reason to make
    paths guessable.
    """
    return f"homework_check/{instance.hw_check_id}/{uuid.uuid4().hex}.jpg"


class Rating(models.TextChoices):
    EXCELLENT = 'excellent', 'Excellent'
    GOOD = 'good', 'Good'
    FAIR = 'fair', 'Fair'
    POOR = 'poor', 'Poor'


class HomeworkCheck(models.Model):
    """A teacher marking one student's exercise from photographs.

    Holds both what the model found (``findings``, ``rating``, ``summary``)
    and what the teacher changed (``teacher_rating``, ``teacher_note``, and
    edits written back into ``findings``). The two are kept apart so an
    unreviewed report is never mistaken for a checked one.
    """

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Awaiting photos'
        ANALYSING = 'analysing', 'Analysing'
        COMPLETE = 'complete', 'Complete'
        FAILED = 'failed', 'Failed'

    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='homework_checks_given',
    )
    teacher_class = models.ForeignKey(
        'homework.TeacherClass', on_delete=models.CASCADE,
        related_name='homework_checks',
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='homework_checks',
    )

    exercise_name = models.CharField(
        max_length=200,
        help_text="What the class calls this piece of work, e.g. 'Ex 5A Q1-8'",
    )
    solution = models.ForeignKey(
        'hw_solutions.HWSolution', on_delete=models.PROTECT,
        related_name='homework_checks',
        help_text="The worked solutions to compare against.",
    )
    solution_pages = models.CharField(
        max_length=60, blank=True,
        help_text="Pages of the solutions to use, e.g. '3-4'. Blank = all of them.",
    )

    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.DRAFT,
    )

    # Raw per-chunk model output kept beside the assembled report: the JSON is
    # for debugging prompt changes, ``findings`` is what the pages render.
    analysis = models.JSONField(default=list, blank=True)
    findings = models.JSONField(default=list, blank=True)
    counts = models.JSONField(default=dict, blank=True)
    notes = models.JSONField(default=list, blank=True)

    summary = models.TextField(blank=True)
    diagram_feedback = models.TextField(blank=True)
    has_diagram = models.BooleanField(default=False)

    # Computed in code from the verdicts, never taken on the model's word, and
    # left blank when the photos did not support one. See services.assembly.
    rating = models.CharField(
        max_length=10, choices=Rating.choices, blank=True,
    )
    rating_reason = models.CharField(
        max_length=200, blank=True,
        help_text="Why no rating was given, when one was withheld.",
    )
    # The teacher's own judgement, which always wins on the printed sheet.
    teacher_rating = models.CharField(
        max_length=10, choices=Rating.choices, blank=True,
    )
    teacher_note = models.TextField(
        blank=True, help_text="The teacher's own note, printed on the report.",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    readable = models.BooleanField(default=True)
    confidence = models.CharField(max_length=8, blank=True)

    model_used = models.CharField(max_length=64, blank=True)
    prompt_tokens = models.PositiveIntegerField(default=0)
    completion_tokens = models.PositiveIntegerField(default=0)

    # Internal only. Never rendered -- the older graders leak str(e) into
    # feedback and this is the deliberate break from that.
    error_message = models.TextField(blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    analysed_at = models.DateTimeField(null=True, blank=True)
    purge_after = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['teacher_class', '-created_at']),
            models.Index(fields=['student', '-created_at']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.student.get_full_name() or self.student.username} — {self.exercise_name}"

    def save(self, *args, **kwargs):
        if not self.purge_after:
            days = getattr(settings, 'HOMEWORK_CHECK_RETENTION_DAYS', 90)
            self.purge_after = (self.created_at or timezone.now()) + timedelta(days=days)
        super().save(*args, **kwargs)

    @property
    def final_rating(self):
        """What the printed sheet shows: the teacher's word over the model's."""
        return self.teacher_rating or self.rating

    @property
    def final_rating_display(self):
        return dict(Rating.choices).get(self.final_rating, "")

    @property
    def is_reviewed(self):
        return self.reviewed_at is not None

    @property
    def chunk_size(self):
        return max(1, getattr(settings, 'HOMEWORK_CHECK_CHUNK_SIZE', 4))

    def pending_photos(self):
        """Photos not yet folded into a chunk result, in upload order."""
        return self.photos.filter(
            status=CheckPhoto.Status.PENDING
        ).order_by('order', 'pk')

    def progress(self):
        """(analysed, total) photos, for the progress bar."""
        total = self.photos.count()
        done = self.photos.exclude(status=CheckPhoto.Status.PENDING).count()
        return done, total


class CheckPhoto(models.Model):
    """One photograph of the student's copy.

    Photos live under PRIVATE_MEDIA_ROOT, not MEDIA_ROOT: on PythonAnywhere
    /media/ is a static mapping served outside Django and cannot be permission
    checked, and these are photographs of a named child's work.
    """

    class Status(models.TextChoices):
        PENDING = 'pending', 'Not yet analysed'
        ANALYSED = 'analysed', 'Analysed'
        FAILED = 'failed', 'Failed'

    # Not "check": that shadows Model.check(), which Django uses for its own
    # system checks and refuses to let a field override.
    hw_check = models.ForeignKey(
        HomeworkCheck, on_delete=models.CASCADE, related_name='photos',
    )
    image = models.ImageField(
        upload_to=check_photo_path, storage=private_storage,
        help_text="Private: served only via the check_photo view, never by URL.",
    )
    order = models.PositiveSmallIntegerField(default=0)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING,
    )
    image_width = models.PositiveIntegerField(null=True, blank=True)
    image_height = models.PositiveIntegerField(null=True, blank=True)
    byte_size = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['order', 'pk']

    def __str__(self):
        return f"Photo {self.order + 1} of check #{self.hw_check_id}"
