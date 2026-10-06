from django.db import models
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from interactive_lessons.models import Question, QuestionPart
from django.contrib.sessions.models import Session
from schools.models import School
from students.storage import private_storage
from datetime import timedelta
import secrets
import uuid



# -------------------------------------------------------------------------
# STUDENT PROFILE
# -------------------------------------------------------------------------
class StudentProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.PROTECT,
        help_text="User account for this student"
    )
    school = models.ForeignKey(
        School,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='students',
        help_text="School this student belongs to"
    )
    total_score = models.FloatField(default=0)
    lessons_completed = models.PositiveIntegerField(default=0)
    last_activity = models.DateTimeField(default=timezone.now)

    def __str__(self):
        """
        Return username. Handles case where user might not exist.
        """
        try:
            return self.user.username
        except User.DoesNotExist:
            return f"StudentProfile #{self.pk} (orphaned)"

    def update_progress(self):
        """Recalculate overall score and lessons completed."""
        attempts = self.attempts.all()
        self.total_score = sum(a.score_awarded for a in attempts)
        self.lessons_completed = (
            attempts.values("question__topic").distinct().count()
        )
        self.last_activity = timezone.now()
        self.save()


# -------------------------------------------------------------------------
# QUESTION ATTEMPT (supports QuestionPart)
# -------------------------------------------------------------------------


class QuestionAttempt(models.Model):
    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name="attempts",
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="attempts",
    )
    question_part = models.ForeignKey(
        QuestionPart,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attempts",
        help_text="Linked part of the question (if applicable)",
    )

    # --- Answer data ---
    student_answer = models.TextField(blank=True)
    score_awarded = models.FloatField(default=0, help_text="Score percentage (0–100).")
    marks_awarded = models.FloatField(default=0, help_text="Actual marks earned for this attempt.")
    feedback = models.TextField(blank=True, help_text="Auto or teacher feedback text.")
    is_correct = models.BooleanField(default=False)

    attempted_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        q_label = f"Q{self.question.id}"
        if self.question_part:
            q_label += f".{self.question_part.label or self.question_part.order}"
        status = "✅" if self.is_correct else "❌"
        return f"{self.student.user.username} – {q_label} ({status})"

    # ✅ Auto-calculate marks_awarded before save
    def save(self, *args, **kwargs):
        """Ensure marks_awarded reflects score_awarded × max_marks."""
        if self.question_part and self.score_awarded is not None:
            try:
                self.marks_awarded = round(
                    (self.score_awarded / 100.0) * float(self.question_part.max_marks or 1), 2
                )
            except Exception:
                self.marks_awarded = 0
        super().save(*args, **kwargs)


class QuestionFeedback(models.Model):
    """Track student feedback (thumbs up/down) on question grading/feedback."""
    FEEDBACK_CHOICES = [
        ('helpful', 'Thumbs Up'),
        ('not_helpful', 'Thumbs Down'),
    ]

    attempt = models.ForeignKey(
        QuestionAttempt,
        on_delete=models.CASCADE,
        related_name='feedback_responses',
        help_text="The question attempt this feedback is for"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='question_feedback',
        help_text="Student who provided feedback"
    )
    feedback_type = models.CharField(
        max_length=20,
        choices=FEEDBACK_CHOICES,
        help_text="Whether student found feedback helpful or not"
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ['attempt', 'user']
        verbose_name = 'Question Feedback'
        verbose_name_plural = 'Question Feedback'

    def __str__(self):
        return f"{self.user.username} - {self.get_feedback_type_display()} - Attempt {self.attempt.id}"


# -------------------------------------------------------------------------
# REGISTRATION CODE
# -------------------------------------------------------------------------
class RegistrationCode(models.Model):
    CODE_TYPE_CHOICES = [
        ('student', 'Student'),
        ('teacher', 'Teacher'),
    ]

    code = models.CharField(max_length=50, unique=True, help_text="Registration code for new signups")
    code_type = models.CharField(
        max_length=10,
        choices=CODE_TYPE_CHOICES,
        default='student',
        help_text="Type of account this code creates (student or teacher)"
    )
    school = models.ForeignKey(
        School,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='registration_codes',
        help_text="School this registration code belongs to"
    )
    teacher_class = models.ForeignKey(
        'homework.TeacherClass',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='registration_codes',
        help_text="If code_type='student', optionally link to a specific class for auto-enrollment"
    )
    is_active = models.BooleanField(default=True, help_text="Whether this code can be used")
    max_uses = models.PositiveIntegerField(default=1, help_text="Maximum number of times this code can be used (0 = unlimited)")
    times_used = models.PositiveIntegerField(default=0, help_text="How many times this code has been used")
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="created_codes")
    description = models.CharField(max_length=200, blank=True, help_text="Optional description (e.g., 'Class of 2025', 'Teacher Access 2025')")

    def __str__(self):
        status = "Active" if self.is_active and not self.is_exhausted() else "Inactive"
        code_type_display = self.get_code_type_display()
        return f"{self.code} ({code_type_display}, {status}) - Used {self.times_used}/{self.max_uses if self.max_uses > 0 else '∞'}"

    def is_exhausted(self):
        """Check if code has reached its usage limit"""
        if self.max_uses == 0:  # unlimited
            return False
        return self.times_used >= self.max_uses

    def can_be_used(self):
        """Check if code is valid and can be used"""
        return self.is_active and not self.is_exhausted()

    def use_code(self):
        """Increment usage counter"""
        self.times_used += 1
        self.save()

    @staticmethod
    def generate_code(length=8, prefix=''):
        """Generate a random registration code with optional prefix"""
        random_part = secrets.token_urlsafe(length)[:length].upper()
        return f"{prefix}{random_part}" if prefix else random_part

    class Meta:
        ordering = ['-created_at']


# -------------------------------------------------------------------------
# LOGIN HISTORY
# -------------------------------------------------------------------------
class LoginHistory(models.Model):
    """Track all login attempts (successful and failed)"""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='login_history',
        null=True,
        blank=True,
        help_text="User who attempted to login (null for failed attempts)"
    )
    username_attempted = models.CharField(
        max_length=150,
        help_text="Username used in login attempt"
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    success = models.BooleanField(default=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, help_text="Browser/device information")
    session_key = models.CharField(max_length=40, blank=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Login History'
        verbose_name_plural = 'Login History'
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['user', '-timestamp']),
        ]

    def __str__(self):
        status = "✓" if self.success else "✗"
        return f"{status} {self.username_attempted} - {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"


# -------------------------------------------------------------------------
# USER SESSION
# -------------------------------------------------------------------------
class UserSession(models.Model):
    """Track active user sessions"""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='active_sessions'
    )
    session_key = models.CharField(
        max_length=40,
        unique=True,
        help_text="Django session key"
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    login_time = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-last_activity']
        verbose_name = 'Active Session'
        verbose_name_plural = 'Active Sessions'

    def __str__(self):
        return f"{self.user.username} - {self.login_time.strftime('%Y-%m-%d %H:%M:%S')}"

    def is_active(self):
        """Check if the session is still valid"""
        try:
            session = Session.objects.get(session_key=self.session_key)
            return session.expire_date > timezone.now()
        except Session.DoesNotExist:
            return False


# -------------------------------------------------------------------------
# WORK SUBMISSIONS  (photographs of handwritten working)
# -------------------------------------------------------------------------
def work_photo_path(instance, filename):
    """Per-student directory, random filename.

    The filename is not the security boundary -- these are served by a view
    that checks ownership -- but there is no reason to make paths guessable.
    """
    return f"work/{instance.student_id}/{uuid.uuid4().hex}.jpg"


class WorkSubmission(models.Model):
    """A photo of a student's handwritten working, and what the AI made of it.

    Deliberately not a field on QuestionAttempt. A photo exists before any
    grading, may be re-analysed, may be deleted on its own for privacy, and in
    this version never produces a mark at all -- so it does not belong on a row
    whose purpose is to record a score.

    Nullable FKs rather than a GenericForeignKey: there are only ever a few
    kinds of target, and real foreign keys give cascade delete and a workable
    admin on MySQL. The third, a homework sheet's exercise plus a question
    number, is for paper homework: the question exists only on the printed
    sheet, so the student names it rather than picking a database row.
    """

    class Status(models.TextChoices):
        AWAITING_PHOTO = 'awaiting', 'Awaiting photo'
        ANALYSING = 'analysing', 'Analysing'
        COMPLETE = 'complete', 'Complete'
        FAILED = 'failed', 'Failed'

    student = models.ForeignKey(
        StudentProfile, on_delete=models.CASCADE, related_name='work_submissions'
    )

    # Exactly one of these is set -- enforced by the constraint below.
    question_part = models.ForeignKey(
        QuestionPart, null=True, blank=True,
        on_delete=models.CASCADE, related_name='work_submissions'
    )
    exam_question_part = models.ForeignKey(
        'exam_papers.ExamQuestionPart', null=True, blank=True,
        on_delete=models.CASCADE, related_name='work_submissions'
    )
    # Homework help: an exercise from a solutions PDF, and which question on
    # the student's sheet. SET_NULL so re-detecting a PDF's exercises cannot
    # take a student's photos with it; the label below still says what it was.
    hw_section = models.ForeignKey(
        'hw_solutions.HWSolutionSection', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='work_submissions'
    )
    hw_question_label = models.CharField(max_length=20, blank=True)

    image = models.ImageField(
        upload_to=work_photo_path, storage=private_storage, blank=True,
        help_text="Private: served only via the work_photo view, never by URL."
    )
    image_width = models.PositiveIntegerField(null=True, blank=True)
    image_height = models.PositiveIntegerField(null=True, blank=True)
    byte_size = models.PositiveIntegerField(default=0)

    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.AWAITING_PHOTO
    )

    # Raw model output kept alongside the flattened columns: the JSON is for
    # debugging prompt changes, the columns for rendering and querying without
    # JSON path expressions on MySQL.
    analysis = models.JSONField(default=dict, blank=True)
    transcription = models.TextField(blank=True)
    method_feedback = models.TextField(blank=True)
    diagram_feedback = models.TextField(blank=True)
    next_step = models.TextField(blank=True)
    has_diagram = models.BooleanField(default=False)
    has_working = models.BooleanField(default=True)
    readable = models.BooleanField(default=True)
    confidence = models.CharField(max_length=8, blank=True)

    # Exam parts only, and only where the part has both a marking scheme image
    # and max_marks. Advisory: shown to the student as an estimate, never
    # written to a QuestionAttempt and never counted in total_score. Null means
    # no mark was given -- unmarkable photo, no scheme, or no working.
    estimated_mark = models.PositiveSmallIntegerField(null=True, blank=True)
    estimated_max_marks = models.PositiveSmallIntegerField(null=True, blank=True)
    mark_reasoning = models.TextField(blank=True)

    model_used = models.CharField(max_length=64, blank=True)
    prompt_tokens = models.PositiveIntegerField(default=0)
    completion_tokens = models.PositiveIntegerField(default=0)

    # Internal only. Never rendered to a student -- the existing graders leak
    # str(e) into feedback and this is the deliberate break from that.
    error_message = models.TextField(blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    analysed_at = models.DateTimeField(null=True, blank=True)
    purge_after = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['student', '-created_at']),
            models.Index(fields=['status']),
        ]
        constraints = [
            # A homework-help row is told apart by its question label, not its
            # section, because the section is SET_NULL and may later vanish.
            models.CheckConstraint(
                condition=(
                    models.Q(question_part__isnull=False, exam_question_part__isnull=True,
                             hw_question_label='')
                    | models.Q(question_part__isnull=True, exam_question_part__isnull=False,
                               hw_question_label='')
                    | (models.Q(question_part__isnull=True, exam_question_part__isnull=True)
                       & ~models.Q(hw_question_label=''))
                ),
                name='worksubmission_exactly_one_target',
            )
        ]

    def __str__(self):
        return f"Work photo #{self.pk} by {self.student} ({self.status})"

    def clean(self):
        # Mirrors the constraint, for admin and forms, and because older MySQL
        # may not enforce CHECK.
        targets = [bool(self.question_part_id), bool(self.exam_question_part_id),
                   bool(self.hw_question_label)]
        if sum(targets) != 1:
            raise ValidationError(
                "Set exactly one of question_part, exam_question_part or a "
                "homework question."
            )

    @property
    def part(self):
        """Whichever part this belongs to. None for a homework-help photo."""
        return self.question_part or self.exam_question_part

    @property
    def is_homework_help(self):
        return bool(self.hw_question_label)

    @property
    def target_label(self):
        """What the photo is of, in words: for the phone page and the admin."""
        if self.is_homework_help:
            exercise = self.hw_section.label if self.hw_section else "Homework"
            return f"{exercise} \u00b7 Q{self.hw_question_label}"
        return str(self.part) if self.part else ""

    def save(self, *args, **kwargs):
        if not self.purge_after:
            days = getattr(settings, 'WORK_PHOTO_RETENTION_DAYS', 90)
            self.purge_after = (self.created_at or timezone.now()) + timedelta(days=days)
        super().save(*args, **kwargs)
