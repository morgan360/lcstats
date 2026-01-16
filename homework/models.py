from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError
from interactive_lessons.models import Topic, Section
from exam_papers.models import ExamQuestion
from quickkicks.models import QuickKick


class TeacherProfile(models.Model):
    """
    Extended profile for teachers to manage their classes and homework.
    Links to User model with is_staff=True.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='teacher_profile',
        limit_choices_to={'is_staff': True},
        help_text="Must be a staff user"
    )
    display_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Display name (e.g., 'Mr. Smith', 'Ms. O'Brien')"
    )
    email = models.EmailField(blank=True, help_text="Contact email")
    is_active = models.BooleanField(default=True, help_text="Can create homework assignments")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.display_name or self.user.get_full_name() or self.user.username

    class Meta:
        verbose_name = "Teacher Profile"
        verbose_name_plural = "Teacher Profiles"


class TeacherClass(models.Model):
    """
    Represents a class/group of students managed by a teacher.
    """
    teacher = models.ForeignKey(
        TeacherProfile,
        on_delete=models.CASCADE,
        related_name='classes',
        help_text="Teacher who manages this class"
    )
    name = models.CharField(
        max_length=200,
        help_text="Class name (e.g., '6th Year Maths A', 'Leaving Cert Group 1')"
    )
    description = models.TextField(
        blank=True,
        help_text="Optional description of the class"
    )
    students = models.ManyToManyField(
        User,
        related_name='enrolled_classes',
        blank=True,
        help_text="Students enrolled in this class"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this class is currently active"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.teacher})"

    def student_count(self):
        return self.students.count()
    student_count.short_description = "Students"

    class Meta:
        verbose_name = "Class"
        verbose_name_plural = "Classes"
        ordering = ['teacher', 'name']


class HomeworkAssignment(models.Model):
    """
    A homework assignment created by a teacher for a specific topic.
    Can be assigned to entire classes or individual students.
    """
    teacher = models.ForeignKey(
        TeacherProfile,
        on_delete=models.CASCADE,
        related_name='assignments',
        help_text="Teacher who created this assignment"
    )
    topic = models.ForeignKey(
        Topic,
        on_delete=models.PROTECT,
        related_name='homework_assignments',
        help_text="Topic this homework covers"
    )
    title = models.CharField(
        max_length=200,
        help_text="Assignment title (e.g., 'Trigonometry Week 1')"
    )
    description = models.TextField(
        blank=True,
        help_text="Instructions or notes for students"
    )

    # Assignment targets
    assigned_classes = models.ManyToManyField(
        TeacherClass,
        related_name='assignments',
        blank=True,
        help_text="Classes assigned this homework"
    )
    assigned_students = models.ManyToManyField(
        User,
        related_name='individual_assignments',
        blank=True,
        help_text="Individual students assigned this homework (in addition to classes)"
    )

    # Timing
    assigned_date = models.DateTimeField(
        default=timezone.now,
        help_text="When this homework was assigned"
    )
    due_date = models.DateTimeField(
        help_text="When this homework is due"
    )

    # Status
    is_published = models.BooleanField(
        default=False,
        help_text="Whether students can see this assignment (draft mode if False)"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - Due {self.due_date.strftime('%Y-%m-%d')}"

    def is_overdue(self):
        """Check if assignment is past due date"""
        return timezone.now() > self.due_date and not self.is_completed()

    def is_completed(self):
        """Check if all tasks are completed (placeholder - implement based on progress)"""
        # This would check StudentHomeworkProgress
        return False

    def get_all_assigned_students(self):
        """Get all students assigned to this homework (from classes + individuals)"""
        from django.db.models import Q
        class_students = User.objects.filter(enrolled_classes__assignments=self)
        individual_students = self.assigned_students.all()
        return (class_students | individual_students).distinct()

    def assign_to_class(self, teacher_class):
        """
        Assign this homework to an entire class in one operation.
        This will:
        1. Add the class to assigned_classes
        2. Create StudentHomeworkProgress records for all students in the class for all tasks

        Args:
            teacher_class: TeacherClass instance to assign homework to

        Returns:
            tuple: (number of students assigned, number of progress records created)
        """
        # Add the class to assigned classes
        self.assigned_classes.add(teacher_class)

        # Get all students in the class
        students = teacher_class.students.all()
        student_count = students.count()

        # Create progress records for each student for each task
        progress_records_created = 0
        for student in students:
            for task in self.tasks.all():
                # Use get_or_create to avoid duplicates
                _, created = StudentHomeworkProgress.objects.get_or_create(
                    student=student,
                    assignment=self,
                    task=task
                )
                if created:
                    progress_records_created += 1

        return (student_count, progress_records_created)

    def assign_to_multiple_classes(self, teacher_classes):
        """
        Assign this homework to multiple classes at once.

        Args:
            teacher_classes: QuerySet or list of TeacherClass instances

        Returns:
            dict: Summary with total students and progress records created
        """
        total_students = 0
        total_progress_records = 0

        for teacher_class in teacher_classes:
            students, progress = self.assign_to_class(teacher_class)
            total_students += students
            total_progress_records += progress

        return {
            'total_students': total_students,
            'total_progress_records': total_progress_records,
            'classes_assigned': len(list(teacher_classes))
        }

    class Meta:
        verbose_name = "Homework Assignment"
        verbose_name_plural = "Homework Assignments"
        ordering = ['-due_date', '-created_at']


class HomeworkTask(models.Model):
    """
    Individual task within a homework assignment.
    Can reference a Section, ExamQuestion, or QuickKick.
    """
    TASK_TYPE_CHOICES = [
        ('section', 'Topic Section'),
        ('exam_question', 'Exam Question'),
        ('quickkick', 'QuickKick Video/Applet'),
    ]

    assignment = models.ForeignKey(
        HomeworkAssignment,
        on_delete=models.CASCADE,
        related_name='tasks',
        help_text="Homework assignment this task belongs to"
    )

    task_type = models.CharField(
        max_length=20,
        choices=TASK_TYPE_CHOICES,
        help_text="Type of content for this task"
    )

    # Polymorphic foreign keys (only one should be set based on task_type)
    section = models.ForeignKey(
        Section,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='homework_tasks',
        help_text="Section to complete (if task_type='section')"
    )
    exam_question = models.ForeignKey(
        ExamQuestion,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='homework_tasks',
        help_text="Exam question to practice (if task_type='exam_question')"
    )
    quickkick = models.ForeignKey(
        QuickKick,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='homework_tasks',
        help_text="QuickKick to watch (if task_type='quickkick')"
    )

    # Task metadata
    instructions = models.TextField(
        blank=True,
        help_text="Specific instructions for this task"
    )
    is_required = models.BooleanField(
        default=True,
        help_text="Whether this task is mandatory or optional"
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order within the assignment"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        content = self.get_content_display()
        return f"{self.assignment.title} - {content}"

    def get_content_display(self):
        """Return the display name of the linked content"""
        if self.task_type == 'section' and self.section:
            return f"Section: {self.section.name}"
        elif self.task_type == 'exam_question' and self.exam_question:
            return f"Exam Q{self.exam_question.question_number}"
        elif self.task_type == 'quickkick' and self.quickkick:
            return f"QuickKick: {self.quickkick.title}"
        return "Unknown task"

    def get_content_url(self):
        """Return URL to access this content"""
        if self.task_type == 'section' and self.section:
            # URL to section's first question or section view
            return f"/interactive/{self.section.topic.slug}/"
        elif self.task_type == 'exam_question' and self.exam_question:
            # Link to the topic's exam questions page
            if self.exam_question.topic:
                return f"/interactive/{self.exam_question.topic.slug}/exam-questions/"
            return f"/exam-papers/"
        elif self.task_type == 'quickkick' and self.quickkick:
            # QuickKicks are accessed via topic slug
            return f"/quickkicks/{self.quickkick.topic.slug}/{self.quickkick.id}/"
        return "#"

    def clean(self):
        """Validate that exactly one content FK is set based on task_type"""
        if self.task_type == 'section' and not self.section:
            raise ValidationError({'section': 'Section is required when task type is "section"'})
        elif self.task_type == 'exam_question' and not self.exam_question:
            raise ValidationError({'exam_question': 'Exam question is required when task type is "exam_question"'})
        elif self.task_type == 'quickkick' and not self.quickkick:
            raise ValidationError({'quickkick': 'QuickKick is required when task type is "quickkick"'})

        # Ensure only the correct FK is set
        if self.task_type != 'section':
            self.section = None
        if self.task_type != 'exam_question':
            self.exam_question = None
        if self.task_type != 'quickkick':
            self.quickkick = None

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Homework Task"
        verbose_name_plural = "Homework Tasks"
        ordering = ['assignment', 'order']


class StudentHomeworkProgress(models.Model):
    """
    Tracks individual student progress on homework tasks.
    """
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='homework_progress'
    )
    assignment = models.ForeignKey(
        HomeworkAssignment,
        on_delete=models.CASCADE,
        related_name='student_progress'
    )
    task = models.ForeignKey(
        HomeworkTask,
        on_delete=models.CASCADE,
        related_name='student_progress'
    )

    # Progress tracking
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Optional student notes
    notes = models.TextField(
        blank=True,
        help_text="Student's notes or reflections on this task"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        status = "✓" if self.is_completed else "○"
        return f"{status} {self.student.username} - {self.task.get_content_display()}"

    def mark_complete(self):
        """Mark this task as completed"""
        if not self.is_completed:
            self.is_completed = True
            self.completed_at = timezone.now()
            self.save()

    def mark_incomplete(self):
        """Mark this task as incomplete"""
        if self.is_completed:
            self.is_completed = False
            self.completed_at = None
            self.save()

    def check_auto_completion(self):
        """
        Check if task should be auto-completed based on student activity.
        Returns True if task was auto-completed, False otherwise.
        """
        if self.is_completed:
            return False  # Already completed

        task = self.task
        student = self.student

        # Check Section completion - if student has attempted questions in this section
        if task.task_type == 'section' and task.section:
            from students.models import QuestionAttempt
            # Check if student has made attempts on questions in this section
            attempts = QuestionAttempt.objects.filter(
                student__user=student,
                question__section=task.section
            ).exists()
            if attempts:
                self.mark_complete()
                return True

        # Check Exam Question completion - if student has attempted this question
        elif task.task_type == 'exam_question' and task.exam_question:
            from exam_papers.models import ExamQuestionAttempt
            attempts = ExamQuestionAttempt.objects.filter(
                exam_attempt__student=student,
                question_part__question=task.exam_question
            ).exists()
            if attempts:
                self.mark_complete()
                return True

        # Check QuickKick completion - if student has viewed this QuickKick
        elif task.task_type == 'quickkick' and task.quickkick:
            from quickkicks.models import QuickKickView
            viewed = QuickKickView.objects.filter(
                user=student,
                quickkick=task.quickkick
            ).exists()
            if viewed:
                self.mark_complete()
                return True

        return False

    class Meta:
        verbose_name = "Student Homework Progress"
        verbose_name_plural = "Student Homework Progress"
        unique_together = ('student', 'assignment', 'task')
        ordering = ['assignment', 'task__order']


class HomeworkSubmission(models.Model):
    """
    Optional: Track when students submit completed homework for teacher review.
    """
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='homework_submissions'
    )
    assignment = models.ForeignKey(
        HomeworkAssignment,
        on_delete=models.CASCADE,
        related_name='submissions'
    )

    submitted_at = models.DateTimeField(auto_now_add=True)
    is_late = models.BooleanField(
        default=False,
        help_text="Whether this was submitted after the due date"
    )

    # Teacher feedback
    teacher_comment = models.TextField(
        blank=True,
        help_text="Teacher's feedback on the submission"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        TeacherProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_submissions'
    )

    def __str__(self):
        late = " (LATE)" if self.is_late else ""
        return f"{self.student.username} - {self.assignment.title}{late}"

    def save(self, *args, **kwargs):
        # Auto-detect if submission is late
        if not self.pk:  # Only on creation
            self.is_late = timezone.now() > self.assignment.due_date
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Homework Submission"
        verbose_name_plural = "Homework Submissions"
        unique_together = ('student', 'assignment')
        ordering = ['-submitted_at']


class HomeworkNotificationSnooze(models.Model):
    """
    Tracks when students snooze homework notifications.
    Notification modal won't show again until snooze expires.
    """
    student = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='homework_snooze'
    )
    snoozed_until = models.DateTimeField(
        help_text="Notification won't show until after this time"
    )

    def __str__(self):
        return f"{self.student.username} - snoozed until {self.snoozed_until.strftime('%Y-%m-%d %H:%M')}"

    def is_active(self):
        """Check if snooze is still active"""
        return timezone.now() < self.snoozed_until

    @classmethod
    def snooze_for_hours(cls, user, hours=24):
        """Snooze notifications for specified hours"""
        snoozed_until = timezone.now() + timezone.timedelta(hours=hours)
        snooze, created = cls.objects.update_or_create(
            student=user,
            defaults={'snoozed_until': snoozed_until}
        )
        return snooze

    class Meta:
        verbose_name = "Homework Notification Snooze"
        verbose_name_plural = "Homework Notification Snoozes"
