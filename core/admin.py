from django.contrib import admin
from .models import Subject


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'display_order', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('display_order', 'name')

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description', 'icon')
        }),
        ('Settings', {
            'fields': ('display_order', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ('created_at', 'updated_at')
