from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from interactive_lessons.models import Question, QuestionPart



# -------------------------------------------------------------------------
# STUDENT PROFILE
# -------------------------------------------------------------------------
class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    total_score = models.FloatField(default=0)
    lessons_completed = models.PositiveIntegerField(default=0)
    last_activity = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.user.username

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
