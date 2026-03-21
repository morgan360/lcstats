from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import (
    TeacherProfile,
    TeacherClass,
    HomeworkAssignment,
    HomeworkTask,
    StudentHomeworkProgress,
    HomeworkSubmission,
    HomeworkNotificationSnooze
)
from .forms import (
    PracticeQuestionsTaskForm,
    ExamQuestionsTaskForm,
    QuickKicksTaskForm,
    FlashcardsTaskForm
)
from interactive_lessons.models import Section
from exam_papers.models import ExamQuestion
from quickkicks.models import QuickKick
from flashcards.models import FlashcardSet


@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'user', 'school', 'email', 'is_active', 'class_count', 'created_at')
    list_filter = ('is_active', 'school', 'created_at')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'display_name', 'email', 'school__name')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Teacher Information', {
            'fields': ('user', 'school', 'display_name', 'email')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def class_count(self, obj):
        return obj.classes.count()
    class_count.short_description = "Classes"


class StudentInlineForClass(admin.TabularInline):
    model = TeacherClass.students.through
    extra = 1
    verbose_name = "Student"
    verbose_name_plural = "Enrolled Students"


@admin.register(TeacherClass)
class TeacherClassAdmin(admin.ModelAdmin):
    list_display = ('name', 'teacher', 'student_count', 'is_active', 'created_at')
    list_filter = ('teacher', 'is_active', 'created_at')
    search_fields = ('name', 'description', 'teacher__display_name', 'teacher__user__username')
    filter_horizontal = ('students',)
    readonly_fields = ('created_at', 'updated_at', 'student_count')

    fieldsets = (
        ('Class Information', {
            'fields': ('teacher', 'name', 'description')
        }),
        ('Students', {
            'fields': ('students', 'student_count')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # If user is a teacher (not superuser), only show their classes
        if not request.user.is_superuser and hasattr(request.user, 'teacher_profile'):
            qs = qs.filter(teacher=request.user.teacher_profile)
        return qs

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        """Filter students by school - teachers can only add students from their school"""
        if db_field.name == "students":
            if not request.user.is_superuser and hasattr(request.user, 'teacher_profile'):
                teacher_profile = request.user.teacher_profile
                # Filter students to only those from same school
                if teacher_profile.school:
                    from django.contrib.auth.models import User
                    from students.models import StudentProfile
                    # Get users who have StudentProfile with same school
                    kwargs["queryset"] = User.objects.filter(
                        studentprofile__school=teacher_profile.school
                    )
        return super().formfield_for_manytomany(db_field, request, **kwargs)


# Base inline class with common functionality
class BaseHomeworkTaskInline(admin.StackedInline):
    model = HomeworkTask
    extra = 1

    # Common fields for all task types
    fields = ('is_required', 'order')

    class Media:
        css = {
            'all': ('/static/admin/css/homework_task_inline.css',)
        }

    def get_formset(self, request, obj=None, **kwargs):
        """Pass the parent assignment to each form via form_kwargs"""
        formset_class = super().get_formset(request, obj, **kwargs)
        parent_obj = obj

        # Customize the formset to pass parent to each form via kwargs
        class CustomFormSet(formset_class):
            def get_form_kwargs(self, index):
                kwargs = super().get_form_kwargs(index)
                # Pass parent assignment through form kwargs
                kwargs['parent_assignment'] = parent_obj
                return kwargs

        return CustomFormSet

    def get_queryset(self, request):
        """Only show tasks of this specific type"""
        qs = super().get_queryset(request)
        # Each subclass will override this to filter by task_type
        return qs


class PracticeQuestionsTaskInline(BaseHomeworkTaskInline):
    form = PracticeQuestionsTaskForm
    verbose_name = "Practice Questions Task"
    verbose_name_plural = "📚 Practice Questions"

    fields = ('section', 'is_required', 'order')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(task_type='section')


class ExamQuestionsTaskInline(BaseHomeworkTaskInline):
    form = ExamQuestionsTaskForm
    verbose_name = "Exam Question Task"
    verbose_name_plural = "📝 Exam Questions"

    fields = ('exam_question', 'is_required', 'order')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(task_type='exam_question')


class QuickKicksTaskInline(BaseHomeworkTaskInline):
    form = QuickKicksTaskForm
    verbose_name = "QuickKick Task"
    verbose_name_plural = "⚡ QuickKicks"

    fields = ('quickkick', 'is_required', 'order')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(task_type='quickkick')


class FlashcardsTaskInline(BaseHomeworkTaskInline):
    form = FlashcardsTaskForm
    verbose_name = "Flashcards Task"
    verbose_name_plural = "🎴 Flashcards"

    fields = ('flashcard_set', 'is_required', 'order')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(task_type='flashcard')


@admin.register(HomeworkAssignment)
class HomeworkAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'teacher',
        'get_subject',
        'topic',
        'assigned_date_short',
        'due_date_short',
        'status_badge',
        'assigned_to_summary',
        'progress_summary'
    )
    list_filter = ('teacher', 'topic__subject', 'topic', 'is_published', 'due_date', 'assigned_date')
    search_fields = ('title', 'description', 'teacher__display_name', 'topic__name')
    filter_horizontal = ('assigned_classes', 'assigned_students')
    readonly_fields = ('created_at', 'updated_at', 'progress_summary', 'notification_sent')
    inlines = [
        PracticeQuestionsTaskInline,
        ExamQuestionsTaskInline,
        QuickKicksTaskInline,
        FlashcardsTaskInline
    ]
    date_hierarchy = 'due_date'

    fieldsets = (
        ('Assignment Details', {
            'fields': ('teacher', 'topic', 'title', 'description', 'assigned_date', 'due_date')
        }),
        ('Assignment Targets', {
            'fields': ('assigned_classes', 'assigned_students'),
            'description': (
                '<strong>Step 1:</strong> Select classes above<br>'
                '<strong>Step 2:</strong> Save the form<br>'
                '<strong>Step 3:</strong> Students from selected classes will be automatically added below<br>'
                '<em>You can also manually add/remove individual students</em>'
            )
        }),
        ('Status', {
            'fields': ('is_published', 'notification_sent', 'progress_summary')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_subject(self, obj):
        """Display the subject of the assignment's topic"""
        return obj.topic.subject.name if obj.topic and obj.topic.subject else "No Subject"
    get_subject.short_description = "Subject"
    get_subject.admin_order_field = 'topic__subject'

    def assigned_date_short(self, obj):
        return obj.assigned_date.strftime('%Y-%m-%d')
    assigned_date_short.short_description = "Assigned"
    assigned_date_short.admin_order_field = 'assigned_date'

    def due_date_short(self, obj):
        now = timezone.now()
        if obj.due_date < now:
            return format_html('<span style="color: red; font-weight: bold;">{}</span>',
                             obj.due_date.strftime('%Y-%m-%d'))
        elif (obj.due_date - now).days <= 2:
            return format_html('<span style="color: orange; font-weight: bold;">{}</span>',
                             obj.due_date.strftime('%Y-%m-%d'))
        return obj.due_date.strftime('%Y-%m-%d')
    due_date_short.short_description = "Due Date"
    due_date_short.admin_order_field = 'due_date'

    def status_badge(self, obj):
        if not obj.is_published:
            return format_html('<span style="background-color: #999; color: white; padding: 3px 8px; border-radius: 3px;">DRAFT</span>')
        elif obj.is_overdue():
            return format_html('<span style="background-color: #dc3545; color: white; padding: 3px 8px; border-radius: 3px;">OVERDUE</span>')
        else:
            return format_html('<span style="background-color: #28a745; color: white; padding: 3px 8px; border-radius: 3px;">ACTIVE</span>')
    status_badge.short_description = "Status"

    def assigned_to_summary(self, obj):
        class_count = obj.assigned_classes.count()
        student_count = obj.assigned_students.count()
        parts = []
        if class_count:
            parts.append(f"{class_count} class{'es' if class_count != 1 else ''}")
        if student_count:
            parts.append(f"{student_count} individual{'s' if student_count != 1 else ''}")
        return ", ".join(parts) if parts else "Not assigned"
    assigned_to_summary.short_description = "Assigned To"

    def progress_summary(self, obj):
        """Show completion progress for this assignment"""
        if not obj.pk:
            return "N/A (save first)"

        total_students = obj.get_all_assigned_students().count()
        if total_students == 0:
            return "No students assigned"

        # Count submissions
        submissions = obj.submissions.count()

        return f"{submissions}/{total_students} students submitted ({int(submissions/total_students*100) if total_students else 0}%)"
    progress_summary.short_description = "Progress"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # If user is a teacher (not superuser), only show their assignments
        if not request.user.is_superuser and hasattr(request.user, 'teacher_profile'):
            qs = qs.filter(teacher=request.user.teacher_profile)
        return qs

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Auto-set teacher to current user if they have a teacher profile
        if db_field.name == "teacher":
            if hasattr(request.user, 'teacher_profile'):
                kwargs["initial"] = request.user.teacher_profile
                if not request.user.is_superuser:
                    kwargs["queryset"] = TeacherProfile.objects.filter(id=request.user.teacher_profile.id)

        # Filter topics by current subject (from session via SubjectMiddleware)
        elif db_field.name == "topic":
            from interactive_lessons.models import Topic
            if hasattr(request, 'current_subject') and request.current_subject:
                kwargs["queryset"] = Topic.objects.filter(subject=request.current_subject)
            else:
                # Fallback: show all topics if no subject in session
                kwargs["queryset"] = Topic.objects.all()

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        """Filter classes and students by school - teachers can only assign to their school"""
        if not request.user.is_superuser and hasattr(request.user, 'teacher_profile'):
            teacher_profile = request.user.teacher_profile

            # Filter classes to only teacher's own classes
            if db_field.name == "assigned_classes":
                kwargs["queryset"] = TeacherClass.objects.filter(teacher=teacher_profile)

            # Filter students to only those from same school
            elif db_field.name == "assigned_students":
                if teacher_profile.school:
                    from django.contrib.auth.models import User
                    kwargs["queryset"] = User.objects.filter(
                        studentprofile__school=teacher_profile.school
                    )
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        """Detect when is_published transitions to True and send email notifications."""
        should_notify = False
        if change and 'is_published' in form.changed_data and obj.is_published:
            # Verify it was previously unpublished
            try:
                old = HomeworkAssignment.objects.get(pk=obj.pk)
                if not old.is_published and not old.notification_sent:
                    should_notify = True
            except HomeworkAssignment.DoesNotExist:
                pass

        super().save_model(request, obj, form, change)

        if should_notify:
            from .services import send_assignment_published_email
            result = send_assignment_published_email(obj)
            obj.notification_sent = True
            obj.save(update_fields=['notification_sent'])

            if result['sent'] > 0:
                self.message_user(
                    request,
                    f"Email notifications sent to {result['sent']} student(s).",
                    level='SUCCESS'
                )
            if result['failed'] > 0:
                self.message_user(
                    request,
                    f"Failed to send {result['failed']} email(s). Check logs for details.",
                    level='WARNING'
                )

    def save_related(self, request, form, formsets, change):
        """
        Auto-populate assigned_students with all students from assigned_classes.
        This runs after the main object is saved but before M2M fields are saved.
        """
        super().save_related(request, form, formsets, change)

        # Get the assignment instance
        obj = form.instance

        # Get all students from assigned classes
        students_from_classes = set()
        for teacher_class in obj.assigned_classes.all():
            students_from_classes.update(teacher_class.students.all())

        # Add these students to assigned_students (if not already there)
        if students_from_classes:
            obj.assigned_students.add(*students_from_classes)

            # Show message to user
            num_added = len(students_from_classes)
            self.message_user(
                request,
                f"Automatically added {num_added} student(s) from selected class(es).",
                level='INFO'
            )


@admin.register(HomeworkTask)
class HomeworkTaskAdmin(admin.ModelAdmin):
    list_display = ('assignment', 'task_type', 'get_content_display', 'is_required', 'order')
    list_filter = ('task_type', 'is_required', 'assignment__teacher')
    search_fields = ('assignment__title', 'section__name', 'exam_question__question_number')
    readonly_fields = ('created_at', 'get_content_display', 'get_content_url', 'task_type')

    fieldsets = (
        ('Assignment', {
            'fields': ('assignment',)
        }),
        ('Task Content', {
            'fields': ('task_type', 'section', 'exam_question', 'quickkick', 'flashcard_set'),
            'description': '📝 View task details. Edit tasks via the assignment form for better filtering.'
        }),
        ('Task Details', {
            'fields': ('is_required', 'order')
        }),
        ('Information', {
            'fields': ('get_content_display', 'get_content_url', 'created_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # If user is a teacher (not superuser), only show tasks from their assignments
        if not request.user.is_superuser and hasattr(request.user, 'teacher_profile'):
            qs = qs.filter(assignment__teacher=request.user.teacher_profile)
        return qs


@admin.register(StudentHomeworkProgress)
class StudentHomeworkProgressAdmin(admin.ModelAdmin):
    list_display = ('student', 'assignment', 'task_summary', 'completion_status', 'completed_at', 'updated_at')
    list_filter = ('is_completed', 'assignment__teacher', 'assignment', 'task__task_type')
    search_fields = ('student__username', 'student__first_name', 'student__last_name',
                    'assignment__title', 'notes')
    readonly_fields = ('created_at', 'updated_at', 'task_summary')

    fieldsets = (
        ('Assignment Info', {
            'fields': ('student', 'assignment', 'task', 'task_summary')
        }),
        ('Progress', {
            'fields': ('is_completed', 'completed_at', 'notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def task_summary(self, obj):
        return obj.task.get_content_display()
    task_summary.short_description = "Task"

    def completion_status(self, obj):
        if obj.is_completed:
            return format_html('<span style="color: green; font-weight: bold;">✓ Complete</span>')
        return format_html('<span style="color: #999;">○ Incomplete</span>')
    completion_status.short_description = "Status"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # If user is a teacher, only show progress for their assignments
        if not request.user.is_superuser and hasattr(request.user, 'teacher_profile'):
            qs = qs.filter(assignment__teacher=request.user.teacher_profile)
        return qs


@admin.register(HomeworkSubmission)
class HomeworkSubmissionAdmin(admin.ModelAdmin):
    list_display = (
        'student',
        'assignment',
        'submitted_at_short',
        'is_late_badge',
        'reviewed_status',
        'reviewed_by'
    )
    list_filter = ('is_late', 'reviewed_at', 'assignment__teacher', 'assignment')
    search_fields = ('student__username', 'student__first_name', 'student__last_name',
                    'assignment__title', 'teacher_comment')
    readonly_fields = ('submitted_at', 'is_late')
    date_hierarchy = 'submitted_at'

    fieldsets = (
        ('Submission Info', {
            'fields': ('student', 'assignment', 'submitted_at', 'is_late')
        }),
        ('Teacher Review', {
            'fields': ('teacher_comment', 'reviewed_by', 'reviewed_at')
        }),
    )

    def submitted_at_short(self, obj):
        return obj.submitted_at.strftime('%Y-%m-%d %H:%M')
    submitted_at_short.short_description = "Submitted"
    submitted_at_short.admin_order_field = 'submitted_at'

    def is_late_badge(self, obj):
        if obj.is_late:
            return format_html('<span style="background-color: #dc3545; color: white; padding: 3px 8px; border-radius: 3px;">LATE</span>')
        return format_html('<span style="background-color: #28a745; color: white; padding: 3px 8px; border-radius: 3px;">ON TIME</span>')
    is_late_badge.short_description = "Timing"

    def reviewed_status(self, obj):
        if obj.reviewed_at:
            return format_html('<span style="color: green;">✓ Reviewed</span>')
        return format_html('<span style="color: #999;">Pending</span>')
    reviewed_status.short_description = "Review Status"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # If user is a teacher, only show submissions for their assignments
        if not request.user.is_superuser and hasattr(request.user, 'teacher_profile'):
            qs = qs.filter(assignment__teacher=request.user.teacher_profile)
        return qs

    def save_model(self, request, obj, form, change):
        # Auto-set reviewed_by and reviewed_at if teacher adds a comment
        if obj.teacher_comment and not obj.reviewed_at:
            obj.reviewed_at = timezone.now()
            if hasattr(request.user, 'teacher_profile'):
                obj.reviewed_by = request.user.teacher_profile
        super().save_model(request, obj, form, change)


@admin.register(HomeworkNotificationSnooze)
class HomeworkNotificationSnoozeAdmin(admin.ModelAdmin):
    list_display = ('student', 'snoozed_until', 'is_active_status')
    list_filter = ('snoozed_until',)
    search_fields = ('student__username', 'student__first_name', 'student__last_name')
    readonly_fields = ('is_active_status',)
    ordering = ('-snoozed_until',)

    def is_active_status(self, obj):
        if obj.is_active():
            return format_html('<span style="color: green; font-weight: bold;">✓ Active</span>')
        return format_html('<span style="color: #999;">Expired</span>')
    is_active_status.short_description = "Status"
