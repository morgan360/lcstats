from django.contrib import admin
from markdownx.admin import MarkdownxModelAdmin
from .models import NewsItem


@admin.register(NewsItem)
class NewsItemAdmin(MarkdownxModelAdmin):
    list_display = ['title', 'category', 'publish_date', 'is_pinned', 'is_dismissible', 'is_active', 'dismissal_count']
    list_filter = ['category', 'is_pinned', 'is_dismissible', 'publish_date']
    search_fields = ['title', 'content']
    date_hierarchy = 'publish_date'
    readonly_fields = ['created_at', 'updated_at', 'dismissal_count']

    fieldsets = (
        ('Content', {
            'fields': ('title', 'content', 'category')
        }),
        ('Publishing', {
            'fields': ('publish_date', 'expiry_date', 'is_pinned', 'is_dismissible')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'created_by', 'dismissal_count'),
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
