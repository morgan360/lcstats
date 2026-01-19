from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from interactive_lessons.models import Question, QuestionPart
from django.contrib.sessions.models import Session
from schools.models import School
import secrets



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
