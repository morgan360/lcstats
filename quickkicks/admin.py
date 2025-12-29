from django.contrib import admin
from .models import QuickKick, QuickKickView


@admin.register(QuickKick)
class QuickKickAdmin(admin.ModelAdmin):
    list_display = ('title', 'topic', 'content_type', 'order', 'created_at')
    list_filter = ('topic', 'content_type', 'created_at')
    search_fields = ('title', 'description', 'topic__name')
    ordering = ('topic', 'order', 'title')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Filter question_part dropdown to only show questions marked as QuickKick suitable"""
        if db_field.name == "question_part":
            from interactive_lessons.models import QuestionPart
            kwargs["queryset"] = QuestionPart.objects.filter(is_quickkick_suitable=True).select_related('question', 'question__topic')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'topic', 'order')
        }),
        ('Content Type', {
            'fields': ('content_type',)
        }),
        ('Video Content', {
            'fields': ('video', 'duration_seconds'),
            'description': 'For video content - upload an MP4 file'
        }),
        ('GeoGebra Content', {
            'fields': ('geogebra_code',),
            'description': 'For GeoGebra applets - enter just the code (e.g., "pvvcyzts")'
        }),
        ('Test Question (Optional)', {
            'fields': ('question_part',),
            'description': 'Add a comprehension test question that appears after the video/applet',
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('topic')


@admin.register(QuickKickView)
class QuickKickViewAdmin(admin.ModelAdmin):
    list_display = ('user', 'quickkick', 'viewed_at', 'answer_submitted', 'answer_correct', 'score_awarded')
    list_filter = ('viewed_at', 'quickkick__topic', 'answer_submitted', 'answer_correct')
    search_fields = ('user__username', 'quickkick__title')
    readonly_fields = ('viewed_at', 'last_attempt_at')
    ordering = ('-viewed_at',)

    fieldsets = (
        ('View Information', {
            'fields': ('user', 'quickkick', 'viewed_at')
        }),
        ('Test Question Results', {
            'fields': ('answer_submitted', 'answer_correct', 'score_awarded', 'attempts', 'last_attempt_at'),
            'description': 'Results for the optional test question (if one is attached)'
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'quickkick', 'quickkick__topic')
