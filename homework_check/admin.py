from django.contrib import admin

from .models import CheckPhoto, HomeworkCheck, InboundScan, ScanAddress, VisionUsage


class CheckPhotoInline(admin.TabularInline):
    model = CheckPhoto
    extra = 0
    # No image preview: these are private-storage files, and PrivateStorage.url()
    # raises by design so a template can never emit a public path for one.
    readonly_fields = ['order', 'status', 'image_width', 'image_height',
                       'byte_size', 'created_at']
    fields = readonly_fields


@admin.register(HomeworkCheck)
class HomeworkCheckAdmin(admin.ModelAdmin):
    list_display = ['student', 'exercise_name', 'teacher_class', 'status',
                    'rating', 'teacher_rating', 'created_at']
    list_filter = ['status', 'rating', 'teacher_class', 'created_at']
    search_fields = ['exercise_name', 'student__username', 'student__first_name',
                     'student__last_name']
    date_hierarchy = 'created_at'
    inlines = [CheckPhotoInline]
    readonly_fields = ['analysis', 'findings', 'counts', 'notes', 'model_used',
                       'prompt_tokens', 'completion_tokens', 'error_message',
                       'created_at', 'analysed_at', 'reviewed_at',
                       'photos_deleted_at', 'photos_deleted_count']

    fieldsets = (
        ('Who and what', {
            'fields': ('teacher', 'teacher_class', 'student', 'exercise_name',
                       'solution', 'solution_pages')
        }),
        ('Result', {
            'fields': ('status', 'rating', 'rating_reason', 'teacher_rating',
                       'summary', 'teacher_note', 'diagram_feedback',
                       'has_diagram', 'readable', 'confidence')
        }),
        ('Raw output', {
            'classes': ('collapse',),
            'fields': ('findings', 'counts', 'notes', 'analysis')
        }),
        ('Cost and housekeeping', {
            'classes': ('collapse',),
            'fields': ('model_used', 'prompt_tokens', 'completion_tokens',
                       'error_message', 'created_at', 'analysed_at',
                       'reviewed_at', 'photos_deleted_at',
                       'photos_deleted_count')
        }),
    )


@admin.register(ScanAddress)
class ScanAddressAdmin(admin.ModelAdmin):
    list_display = ['teacher', 'address', 'created_at']
    readonly_fields = ['token', 'created_at']


@admin.register(InboundScan)
class InboundScanAdmin(admin.ModelAdmin):
    """Waiting scans, for support. No file links: they are private storage,
    and PrivateStorage.url() raises by design."""
    list_display = ['teacher', 'filename', 'page_count', 'problem', 'received_at']
    list_filter = ['teacher']
    fields = ['teacher', 'received_at', 'sender', 'subject', 'filename',
              'page_count', 'problem']
    readonly_fields = fields


@admin.register(VisionUsage)
class VisionUsageAdmin(admin.ModelAdmin):
    """What each vision call cost; the spend page's Gemini figures come from here."""
    list_display = ['created_at', 'model', 'hw_check', 'prompt_tokens',
                    'cached_tokens', 'completion_tokens', 'cost_usd']
    list_filter = ['model']
    readonly_fields = [f.name for f in VisionUsage._meta.fields]

    def has_add_permission(self, request):
        return False
