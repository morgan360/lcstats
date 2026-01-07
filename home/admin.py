from django.contrib import admin
from django.utils.html import format_html
from markdownx.admin import MarkdownxModelAdmin
from .models import NewsItem


@admin.register(NewsItem)
class NewsItemAdmin(MarkdownxModelAdmin):
    list_display = ['title', 'target_audience', 'category', 'publish_date', 'is_pinned', 'is_dismissible', 'is_active', 'dismissal_count']
    list_filter = ['category', 'is_pinned', 'is_dismissible', 'publish_date', 'target_classes']
    search_fields = ['title', 'content']
    filter_horizontal = ['target_classes']
    date_hierarchy = 'publish_date'
    readonly_fields = ['created_at', 'updated_at', 'dismissal_count', 'target_audience_display']

    fieldsets = (
        ('Content', {
            'fields': ('title', 'content', 'category')
        }),
        ('Audience', {
            'fields': ('target_classes',),
            'description': 'Leave empty for a general announcement to all students. Select specific classes for targeted announcements.'
        }),
        ('Publishing', {
            'fields': ('publish_date', 'expiry_date', 'is_pinned', 'is_dismissible')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'created_by', 'dismissal_count', 'target_audience_display'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        """Auto-set created_by to current user on creation"""
        if not change:  # New object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def dismissal_count(self, obj):
        """Show how many students have dismissed this item"""
        return obj.dismissed_by.count()
    dismissal_count.short_description = 'Dismissed by'

    def target_audience(self, obj):
        """Show target audience in list view"""
        if obj.is_general():
            return format_html('<span style="color: blue;">🌍 All Students</span>')
        else:
            class_count = obj.target_classes.count()
            return format_html('<span style="color: green;">🎯 {} class{}</span>',
                             class_count,
                             'es' if class_count != 1 else '')
    target_audience.short_description = 'Audience'

    def target_audience_display(self, obj):
        """Show detailed target audience in detail view"""
        return obj.get_target_class_names()
    target_audience_display.short_description = 'Target Audience'
