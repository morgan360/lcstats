from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    total_score = models.FloatField(default=0)
    lessons_completed = models.PositiveIntegerField(default=0)
    last_activity = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.user.username

