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


class HomeworkTaskInline(admin.StackedInline):
    model = HomeworkTask
    extra = 1

    fieldsets = (
        (None, {
            'fields': (
                'task_type',
                'section',
                'exam_question',
                'quickkick',
                'flashcard_set',
                'is_required',
                'order',
                'instructions'
            ),
            'description': '👇 Select task type first, then fill in ONLY the matching field below'
        }),
    )

    class Media:
        css = {
            'all': ('/static/admin/css/homework_task_inline.css',)
        }

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Add custom help text to show when each field should be used"""
        if db_field.name == "section":
            kwargs["help_text"] = "📝 Fill this ONLY if Task Type = 'Topic Section'"
        elif db_field.name == "exam_question":
            kwargs["help_text"] = "📝 Fill this ONLY if Task Type = 'Exam Question'"
        elif db_field.name == "quickkick":
            kwargs["help_text"] = "📝 Fill this ONLY if Task Type = 'QuickFlicks Video/Applet'"
        elif db_field.name == "flashcard_set":
            kwargs["help_text"] = "📝 Fill this ONLY if Task Type = 'Flashcard Set'"
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        return formset


@admin.register(HomeworkAssignment)
class HomeworkAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'teacher',
        'topic',
        'assigned_date_short',
        'due_date_short',
        'status_badge',
        'assigned_to_summary',
        'progress_summary'
    )
    list_filter = ('teacher', 'topic', 'is_published', 'due_date', 'assigned_date')
    search_fields = ('title', 'description', 'teacher__display_name', 'topic__name')
    filter_horizontal = ('assigned_classes', 'assigned_students')
    readonly_fields = ('created_at', 'updated_at', 'progress_summary')
    inlines = [HomeworkTaskInline]
    date_hierarchy = 'due_date'

    class Media:
        js = ('/static/admin/js/homework_assignment_admin.js',)

    fieldsets = (
        ('Assignment Details', {
            'fields': ('teacher', 'topic', 'title', 'description')
        }),
        ('Assignment Targets', {
            'fields': ('assigned_classes', 'assigned_students'),
            'description': 'Assign to entire classes or individual students (or both)'
        }),
        ('Timing', {
            'fields': ('assigned_date', 'due_date')
        }),
        ('Status', {
            'fields': ('is_published', 'progress_summary')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

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
    search_fields = ('assignment__title', 'instructions', 'section__name', 'exam_question__question_number')
    readonly_fields = ('created_at', 'get_content_display', 'get_content_url')

    fieldsets = (
        ('Assignment', {
            'fields': ('assignment',)
        }),
        ('Task Content', {
            'fields': ('task_type', 'section', 'exam_question', 'quickkick', 'flashcard_set'),
            'description': 'Select ONE content item based on task type'
        }),
        ('Task Details', {
            'fields': ('instructions', 'is_required', 'order')
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
