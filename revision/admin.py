from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count
from .models import RevisionModule, RevisionSection


class RevisionSectionInline(admin.TabularInline):
    """Inline editor for revision sections within a module"""
    model = RevisionSection
    extra = 1
    fields = [
        'order',
        'title',
        'text_content',
        'image',
        'image_caption',
        'geogebra_enabled',
        'geogebra_material_id',
        'video_enabled',
        'video_url',
    ]
    ordering = ['order']

    def get_queryset(self, request):
        """Optimize query to reduce DB hits"""
        qs = super().get_queryset(request)
        return qs.select_related('module')


@admin.register(RevisionModule)
class RevisionModuleAdmin(admin.ModelAdmin):
    """Admin interface for revision modules"""
    list_display = [
        'title',
        'topic_name',
        'section_count',
        'is_published',
        'order',
        'updated_at'
    ]
    list_filter = ['is_published', 'topic', 'created_at']
    search_fields = ['title', 'description', 'topic__name']
    list_editable = ['is_published', 'order']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = [
        ('Basic Information', {
            'fields': ['topic', 'title', 'description']
        }),
        ('Publication Settings', {
            'fields': ['is_published', 'order']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        })
    ]

    inlines = [RevisionSectionInline]

    def topic_name(self, obj):
        """Display the related topic name"""
        return obj.topic.name
    topic_name.short_description = 'Topic'
    topic_name.admin_order_field = 'topic__name'

    def section_count(self, obj):
        """Display the number of sections in this module"""
        count = obj.sections.count()
        if count == 0:
            return format_html('<span style="color: #999;">No sections</span>')
        return format_html('<strong>{}</strong> section{}', count, 's' if count != 1 else '')
    section_count.short_description = 'Sections'

    def get_queryset(self, request):
        """Optimize query to reduce DB hits"""
        qs = super().get_queryset(request)
        return qs.select_related('topic').annotate(
            section_count=Count('sections')
        )


@admin.register(RevisionSection)
class RevisionSectionAdmin(admin.ModelAdmin):
    """Admin interface for individual revision sections"""
    list_display = [
        'title',
        'module_name',
        'order',
        'content_types',
        'updated_at'
    ]
    list_filter = ['module', 'geogebra_enabled', 'video_enabled', 'created_at']
    search_fields = ['title', 'text_content', 'module__title']
    list_editable = ['order']
    readonly_fields = ['created_at', 'updated_at', 'content_preview']

    fieldsets = [
        ('Basic Information', {
            'fields': ['module', 'title', 'order']
        }),
        ('Text Content', {
            'fields': ['text_content'],
            'description': 'Supports Markdown and LaTeX. Use $...$ for inline math, $$...$$ for display math.'
        }),
        ('Image', {
            'fields': ['image', 'image_caption'],
            'classes': ['collapse']
        }),
        ('GeoGebra Integration', {
            'fields': [
                'geogebra_enabled',
                'geogebra_material_id',
                'geogebra_width',
                'geogebra_height',
                'geogebra_show_toolbar',
                'geogebra_show_menu'
            ],
            'classes': ['collapse'],
            'description': 'Add interactive GeoGebra visualizations. Get Material ID from geogebra.org (e.g., from URL geogebra.org/m/abcd1234, use "abcd1234")'
        }),
        ('Video Integration', {
            'fields': ['video_enabled', 'video_url', 'video_caption'],
            'classes': ['collapse'],
            'description': 'Embed YouTube videos or direct video URLs'
        }),
        ('Preview', {
            'fields': ['content_preview'],
            'classes': ['collapse']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        })
    ]

    def module_name(self, obj):
        """Display the related module name"""
        return obj.module.title
    module_name.short_description = 'Module'
    module_name.admin_order_field = 'module__title'

    def content_types(self, obj):
        """Display icons for content types in this section"""
        types = []
        if obj.text_content:
            types.append('📝 Text')
        if obj.image:
            types.append('🖼️ Image')
        if obj.geogebra_enabled and obj.geogebra_material_id:
            types.append('📐 GeoGebra')
        if obj.video_enabled and obj.video_url:
            types.append('🎥 Video')

        if not types:
            return format_html('<span style="color: #999;">No content</span>')

        return format_html(' | '.join(types))
    content_types.short_description = 'Content'

    def content_preview(self, obj):
        """Display a preview of the section content"""
        html_parts = []

        # Text preview
        if obj.text_content:
            preview_text = obj.text_content[:200]
            if len(obj.text_content) > 200:
                preview_text += '...'
            html_parts.append(f'<h4>Text Content:</h4><p>{preview_text}</p>')

        # Image preview
        if obj.image:
            html_parts.append(f'''
                <h4>Image:</h4>
                <img src="{obj.image.url}" style="max-width: 400px; max-height: 300px;" alt="{obj.image_caption}">
                {f'<p><em>{obj.image_caption}</em></p>' if obj.image_caption else ''}
            ''')

        # GeoGebra info
        if obj.geogebra_enabled and obj.geogebra_material_id:
            html_parts.append(f'''
                <h4>GeoGebra:</h4>
                <p><strong>Material ID:</strong> {obj.geogebra_material_id}</p>
                <p><strong>Size:</strong> {obj.geogebra_width}x{obj.geogebra_height}px</p>
                <p><strong>Preview:</strong> <a href="https://www.geogebra.org/m/{obj.geogebra_material_id}" target="_blank">View on GeoGebra</a></p>
            ''')

        # Video info
        if obj.video_enabled and obj.video_url:
            html_parts.append(f'''
                <h4>Video:</h4>
                <p><strong>URL:</strong> <a href="{obj.video_url}" target="_blank">{obj.video_url}</a></p>
                {f'<p><em>{obj.video_caption}</em></p>' if obj.video_caption else ''}
            ''')

        if not html_parts:
            return format_html('<p style="color: #999;">No content to preview</p>')

        return format_html('<div style="padding: 10px; background: #f5f5f5; border-radius: 5px;">{}</div>',
                          format_html(''.join(html_parts)))
    content_preview.short_description = 'Content Preview'

    def get_queryset(self, request):
        """Optimize query to reduce DB hits"""
        qs = super().get_queryset(request)
        return qs.select_related('module', 'module__topic')


# Customize the admin site header
admin.site.site_header = "NumScoil Administration"
admin.site.site_title = "NumScoil Admin"
admin.site.index_title = "Welcome to NumScoil Administration"
