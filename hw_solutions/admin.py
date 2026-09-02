from django.contrib import admin

from .models import HWSolution, HWSolutionPage, HWSolutionSection


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
