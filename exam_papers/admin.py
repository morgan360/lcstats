# exam_papers/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import (
    AnswerFormatTemplate,
    ExamPaper,
    ExamQuestion,
    ExamQuestionPart,
    ExamAttempt,
    ExamQuestionAttempt
)


@admin.register(AnswerFormatTemplate)
class AnswerFormatTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'description_preview', 'example', 'is_active', 'order')
    list_filter = ('category', 'is_active')
    search_fields = ('name', 'description', 'category', 'example')
    list_editable = ('order', 'is_active')

    fieldsets = (
        ('Template Information', {
            'fields': ('name', 'category', 'is_active', 'order')
        }),
        ('Format Instructions', {
            'fields': ('description', 'example'),
            'description': 'The description will be shown to students. The example is optional but helpful.'
        }),
    )

    def description_preview(self, obj):
        """Show truncated description in list view"""
        if len(obj.description) > 60:
            return obj.description[:60] + '...'
        return obj.description
    description_preview.short_description = 'Description'


class ExamQuestionPartInline(admin.TabularInline):
    """Inline admin for question parts"""
    model = ExamQuestionPart
    extra = 1
    fields = ('label', 'prompt', 'answer', 'answer_format_template', 'expected_type', 'max_marks', 'order')
    ordering = ['order']
    autocomplete_fields = ['answer_format_template']


class ExamQuestionInline(admin.TabularInline):
    """Inline admin for questions within an exam paper"""
    model = ExamQuestion
    extra = 1
    fields = ('question_number', 'topic', 'title', 'total_marks', 'suggested_time_minutes', 'order')
    ordering = ['order']
    show_change_link = True  # Allow clicking through to edit full question


@admin.register(ExamPaper)
class ExamPaperAdmin(admin.ModelAdmin):
    list_display = ('title', 'year', 'paper_type', 'total_marks', 'time_limit_minutes', 'is_published', 'pdf_link', 'created_at')
    list_filter = ('year', 'paper_type', 'is_published')
    search_fields = ('title', 'year')
    prepopulated_fields = {'slug': ('year', 'paper_type')}

    fieldsets = (
        ('Basic Information', {
            'fields': ('year', 'paper_type', 'title', 'slug', 'is_published')
        }),
        ('Exam Details', {
            'fields': ('time_limit_minutes', 'total_marks', 'instructions')
        }),
        ('Resources', {
            'fields': ('source_pdf', 'marking_scheme_pdf', 'pdf_preview'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ('pdf_preview',)
    inlines = [ExamQuestionInline]

    def pdf_link(self, obj):
        """Show clickable PDF link in list view"""
        if obj.source_pdf:
            return format_html(
                '<a href="{}" target="_blank">View PDF</a>',
                obj.source_pdf.url
            )
        return '-'
    pdf_link.short_description = 'PDF'

    def pdf_preview(self, obj):
        """Show PDF preview in change form"""
        if obj.source_pdf:
            return format_html(
                '<iframe src="{}" width="100%" height="600px" style="border: 1px solid #ccc;"></iframe><br>'
                '<a href="{}" target="_blank" class="button">Open PDF in New Tab</a><br><br>'
                '<strong>Extract Questions:</strong><br>'
                '<code>python manage.py extract_exam_questions {} --preview</code><br>'
                '<code>python manage.py extract_exam_questions {} --num-questions 8</code><br>'
                '<code>python manage.py extract_exam_questions {} --page-ranges "1:1-1,2:2-3,3:4-4"</code>',
                obj.source_pdf.url,
                obj.source_pdf.url,
                obj.id,
                obj.id,
                obj.id
            )
        return 'No PDF uploaded yet'
    pdf_preview.short_description = 'PDF Preview & Extraction'


@admin.register(ExamQuestion)
class ExamQuestionAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'question_number', 'topic', 'total_marks', 'suggested_time_minutes', 'has_image', 'exam_paper')
    list_filter = ('exam_paper__year', 'exam_paper__paper_type', 'topic')
    search_fields = ('title', 'question_number')

    fieldsets = (
        ('Question Identification', {
            'fields': ('exam_paper', 'question_number', 'order')
        }),
        ('Content', {
            'fields': ('topic', 'title', 'image', 'image_preview')
        }),
        ('Marking & Timing', {
            'fields': ('total_marks', 'suggested_time_minutes')
        }),
    )

    readonly_fields = ('image_preview',)
    inlines = [ExamQuestionPartInline]

    def has_image(self, obj):
        """Show if question has image"""
        return '✓' if obj.image else '-'
    has_image.short_description = 'Image'

    def image_preview(self, obj):
        """Show question image preview for easy transcription"""
        if obj.image:
            return format_html(
                '<div style="border: 2px solid #4CAF50; padding: 15px; background: #f9f9f9;">'
                '<h3 style="margin-top: 0;">Question Image (for transcription reference)</h3>'
                '<img src="{}" style="max-width: 100%; border: 1px solid #ddd; margin-bottom: 10px;"><br>'
                '<a href="{}" target="_blank" class="button">Open Full Size</a>'
                '<p style="color: #666; font-size: 12px; margin-top: 10px;">'
                '<strong>Tip:</strong> Use this image as reference while filling in the question parts below. '
                'You can also use the /extract-question command with this image.'
                '</p>'
                '</div>',
                obj.image.url,
                obj.image.url
            )
        return 'No image extracted yet. Run extract_exam_questions command first.'
    image_preview.short_description = 'Question Image Reference'


@admin.register(ExamQuestionPart)
class ExamQuestionPartAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'label', 'question', 'expected_type', 'max_marks', 'solution_unlock_after_attempts')
    list_filter = ('expected_type', 'question__exam_paper__year', 'question__topic')
    search_fields = ('label', 'prompt', 'question__title')

    fieldsets = (
        ('Part Identification', {
            'fields': ('question', 'label', 'order')
        }),
        ('Question Content', {
            'fields': ('prompt', 'image')
        }),
        ('Answer Format', {
            'fields': ('answer_format_template', 'expected_format'),
            'description': 'Select a template for common formats, or enter custom text. Template takes precedence.'
        }),
        ('Answer', {
            'fields': ('answer', 'expected_type')
        }),
        ('Solution', {
            'fields': ('solution', 'solution_image', 'solution_unlock_after_attempts')
        }),
        ('Marking', {
            'fields': ('max_marks',)
        }),
    )

    autocomplete_fields = ['answer_format_template']


class ExamQuestionAttemptInline(admin.TabularInline):
    """Inline admin for individual question attempts within an exam attempt"""
    model = ExamQuestionAttempt
    extra = 0
    fields = ('question_part', 'student_answer', 'marks_awarded', 'max_marks', 'attempt_number', 'hint_used', 'solution_viewed')
    readonly_fields = ('submitted_at',)
    can_delete = False


@admin.register(ExamAttempt)
class ExamAttemptAdmin(admin.ModelAdmin):
    list_display = ('student', 'exam_paper', 'attempt_mode', 'percentage_score', 'is_completed', 'started_at')
    list_filter = ('attempt_mode', 'is_completed', 'is_submitted', 'exam_paper__year', 'exam_paper__paper_type')
    search_fields = ('student__username', 'student__email', 'exam_paper__title')
    date_hierarchy = 'started_at'

    fieldsets = (
        ('Attempt Information', {
            'fields': ('student', 'exam_paper', 'attempt_mode')
        }),
        ('Timing', {
            'fields': ('started_at', 'completed_at', 'time_spent_seconds')
        }),
        ('Scoring', {
            'fields': ('total_marks_awarded', 'total_marks_possible', 'percentage_score')
        }),
        ('Status', {
            'fields': ('is_completed', 'is_submitted')
        }),
    )

    readonly_fields = ('started_at', 'percentage_score')
    inlines = [ExamQuestionAttemptInline]

    def get_readonly_fields(self, request, obj=None):
        """Make scoring fields read-only if attempt exists"""
        if obj:  # Editing existing object
            return self.readonly_fields + ('student', 'exam_paper', 'started_at')
        return self.readonly_fields


@admin.register(ExamQuestionAttempt)
class ExamQuestionAttemptAdmin(admin.ModelAdmin):
    list_display = ('student_username', 'question_part', 'marks_awarded', 'max_marks', 'attempt_number', 'submitted_at')
    list_filter = ('is_correct', 'hint_used', 'solution_viewed', 'question_part__expected_type')
    search_fields = ('exam_attempt__student__username', 'question_part__label', 'student_answer')
    date_hierarchy = 'submitted_at'

    fieldsets = (
        ('Attempt Information', {
            'fields': ('exam_attempt', 'question_part', 'attempt_number')
        }),
        ('Student Answer', {
            'fields': ('student_answer',)
        }),
        ('Grading', {
            'fields': ('marks_awarded', 'max_marks', 'is_correct', 'feedback')
        }),
        ('Metadata', {
            'fields': ('time_spent_seconds', 'hint_used', 'solution_viewed', 'submitted_at')
        }),
    )

    readonly_fields = ('submitted_at',)

    def student_username(self, obj):
        return obj.exam_attempt.student.username
    student_username.short_description = 'Student'
    student_username.admin_order_field = 'exam_attempt__student__username'


# Customize admin site header
admin.site.site_header = "LCAI Maths - Exam Papers Administration"
admin.site.site_title = "Exam Papers Admin"
admin.site.index_title = "Exam Papers Management"