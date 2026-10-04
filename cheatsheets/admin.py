from django.contrib import admin
from .models import CheatSheet


@admin.register(CheatSheet)
class CheatSheetAdmin(admin.ModelAdmin):
    list_display = ['title', 'kind', 'topic', 'order', 'created_at']
    list_filter = ['kind', 'topic', 'created_at']
    search_fields = ['title', 'description', 'topic__name']
    ordering = ['topic__name', 'order', 'title']
    list_editable = ['order']

    fieldsets = (
        ('Basic Information', {
            'fields': ('kind', 'topic', 'title', 'description')
        }),
        ('File', {
            'fields': ('pdf_file',)
        }),
        ('Display Options', {
            'fields': ('order',)
        }),
    )
