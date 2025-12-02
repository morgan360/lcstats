from django.contrib import admin
from .models import QuickKick


@admin.register(QuickKick)
class QuickKickAdmin(admin.ModelAdmin):
    list_display = ('title', 'topic', 'content_type', 'order', 'created_at')
    list_filter = ('topic', 'content_type', 'created_at')
    search_fields = ('title', 'description', 'topic__name')
    ordering = ('topic', 'order', 'title')

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
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('topic')
