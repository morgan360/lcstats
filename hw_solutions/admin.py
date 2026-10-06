from django.contrib import admin

from .models import HWSolution, HWSolutionPage, HWSolutionSection


@admin.register(HWSolution)
class HWSolutionAdmin(admin.ModelAdmin):
    list_display = ['title', 'subject', 'is_released', 'order', 'created_at']
    list_filter = ['subject', 'is_released', 'created_at']
    search_fields = ['title', 'description']
    list_editable = ['is_released', 'order']

    fieldsets = (
        ('Basic Information', {
            'fields': ('subject', 'title', 'description')
        }),
        ('File', {
            'fields': ('pdf_file',)
        }),
        ('Display Options', {
            'fields': ('is_released', 'order')
        }),
    )


@admin.register(HWSolutionPage)
class HWSolutionPageAdmin(admin.ModelAdmin):
    list_display = ['solution', 'page_number', 'created_at']
    list_filter = ['solution']
    readonly_fields = ['created_at']


@admin.register(HWSolutionSection)
class HWSolutionSectionAdmin(admin.ModelAdmin):
    list_display = ['solution', 'label', 'first_page', 'last_page', 'page_count']
    list_filter = ['solution']
    search_fields = ['label']
