from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from interactive_lessons.models import Question  # ✅ use the shared Question model


class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    total_score = models.FloatField(default=0)
    lessons_completed = models.PositiveIntegerField(default=0)
    last_activity = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.user.username

    def update_progress(self):
        attempts = self.attempts.all()
        self.total_score = sum(a.score_awarded for a in attempts)
        self.lessons_completed = attempts.values("question__topic").distinct().count()
        self.last_activity = timezone.now()
        self.save()


class QuestionAttempt(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="attempts")
    question = models.ForeignKey(Question, on_delete=models.CASCADE)  # ✅ reference interactive_lessons.Question
    student_answer = models.TextField(blank=True)
    score_awarded = models.FloatField(default=0)
    is_correct = models.BooleanField(default=False)
    attempted_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.student.user.username} – Q{self.question.id} ({'✅' if self.is_correct else '❌'})"
