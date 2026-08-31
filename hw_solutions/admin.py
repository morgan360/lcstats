from django.contrib import admin

from .models import HWSolution


@admin.register(HWSolution)
class HWSolutionAdmin(admin.ModelAdmin):
    list_display = ['title', 'subject', 'order', 'created_at']
    list_filter = ['subject', 'created_at']
    search_fields = ['title', 'description']
    list_editable = ['order']

    fieldsets = (
        ('Basic Information', {
            'fields': ('subject', 'title', 'description')
        }),
        ('File', {
            'fields': ('pdf_file',)
        }),
        ('Display Options', {
            'fields': ('order',)
        }),
    )
