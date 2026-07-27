from django.conf import settings
from django.db import models


class CommentPreset(models.Model):
    """
    Admin-managed dropdown options for behaviour/test comments,
    so daily entry on a phone is one tap instead of typing.
    """
    CATEGORY_CHOICES = [
        ('behaviour', 'Behaviour'),
        ('test', 'Test'),
    ]
    TONE_CHOICES = [
        ('positive', 'Positive'),
        ('neutral', 'Neutral'),
        ('concern', 'Concern'),
    ]

    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    tone = models.CharField(max_length=20, choices=TONE_CHOICES, default='neutral')
    text = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['category', 'order', 'text']

    def __str__(self):
        return f"[{self.get_category_display()}/{self.get_tone_display()}] {self.text}"


class TimetableSlot(models.Model):
    """
    When a class meets each week. Set-once-per-year data, managed in Django admin.
    Drives the 'Today' section on the reports dashboard and double-period support.
    """
    WEEKDAY_CHOICES = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]

    teacher_class = models.ForeignKey(
        'homework.TeacherClass',
        on_delete=models.CASCADE,
        related_name='timetable_slots',
    )
    weekday = models.IntegerField(choices=WEEKDAY_CHOICES)
    start_time = models.TimeField()
    label = models.CharField(max_length=60, blank=True, help_text="e.g. 'Period 3' or a room number")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['weekday', 'start_time']

    def __str__(self):
        label = f" ({self.label})" if self.label else ""
        return f"{self.teacher_class.name} — {self.get_weekday_display()} {self.start_time:%H:%M}{label}"


class ClassSession(models.Model):
    """
    One class meeting. Created automatically when the teacher opens daily entry
    for a class/date; ad-hoc sessions (no timetable) have slot=None.
    """
    teacher_class = models.ForeignKey(
        'homework.TeacherClass',
        on_delete=models.CASCADE,
        related_name='sessions',
    )
    date = models.DateField()
    slot = models.ForeignKey(
        TimetableSlot,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='sessions',
    )
    notes = models.TextField(blank=True)
    homework_due = models.BooleanField(
        default=True,
        help_text="Untick when no homework was set for this session, so the day doesn't count against homework rates",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['teacher_class', 'date', 'slot'], name='uniq_session_class_date_slot'),
        ]
        indexes = [
            models.Index(fields=['teacher_class', '-date']),
        ]
        ordering = ['-date']

    def __str__(self):
        slot = f" @ {self.slot.start_time:%H:%M}" if self.slot else ""
        return f"{self.teacher_class.name} — {self.date}{slot}"


class StudentSessionRecord(models.Model):
    """
    Per-student record for one session: attendance + paper homework + behaviour
    comment. Defaults are the no-news-is-good-news state (present, homework done)
    so the teacher only taps exceptions.
    """
    ATTENDANCE_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
    ]
    HOMEWORK_CHOICES = [
        ('done', 'Done'),
        ('partial', 'Partial'),
        ('not_done', 'Not done'),
    ]

    session = models.ForeignKey(ClassSession, on_delete=models.CASCADE, related_name='records')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='session_records')
    attendance = models.CharField(max_length=10, choices=ATTENDANCE_CHOICES, default='present')
    homework = models.CharField(max_length=10, choices=HOMEWORK_CHOICES, default='done')
    comment_preset = models.ForeignKey(
        CommentPreset,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='session_records',
        limit_choices_to={'category': 'behaviour'},
    )
    comment_text = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['session', 'student'], name='uniq_record_session_student'),
        ]

    def __str__(self):
        return f"{self.student.username} — {self.session}"

    @property
    def has_comment(self):
        return bool(self.comment_preset_id or self.comment_text)


class ClassTest(models.Model):
    """A class test (in-school, on paper) whose results are entered manually."""
    teacher_class = models.ForeignKey(
        'homework.TeacherClass',
        on_delete=models.CASCADE,
        related_name='tests',
    )
    name = models.CharField(max_length=120)
    date = models.DateField()
    max_marks = models.PositiveIntegerField(default=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['teacher_class', '-date']),
        ]
        ordering = ['-date']

    def __str__(self):
        return f"{self.name} ({self.teacher_class.name}, {self.date})"


class TestResult(models.Model):
    """One student's result in a ClassTest. score=None means they didn't sit it."""
    test = models.ForeignKey(ClassTest, on_delete=models.CASCADE, related_name='results')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='test_results')
    score = models.DecimalField(max_digits=6, decimal_places=1, null=True, blank=True)
    comment_preset = models.ForeignKey(
        CommentPreset,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='test_results',
        limit_choices_to={'category': 'test'},
    )
    comment_text = models.CharField(max_length=300, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['test', 'student'], name='uniq_result_test_student'),
        ]

    def __str__(self):
        return f"{self.student.username} — {self.test.name}: {self.score if self.score is not None else '—'}"

    @property
    def percentage(self):
        if self.score is None or not self.test.max_marks:
            return None
        return round(float(self.score) / self.test.max_marks * 100, 1)

    @property
    def has_comment(self):
        return bool(self.comment_preset_id or self.comment_text)
