from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import FlashcardSet, Flashcard, FlashcardAttempt


class FlashcardInline(admin.TabularInline):
    """Inline editor for flashcards within a set"""
    model = Flashcard
    extra = 1
    fields = ['order', 'front_text', 'back_text', 'distractor_1', 'distractor_2', 'distractor_3']
    ordering = ['order']


@admin.register(FlashcardSet)
class FlashcardSetAdmin(admin.ModelAdmin):
    list_display = ['title', 'topic', 'card_count_display', 'is_published', 'order', 'updated_at']
    list_filter = ['topic', 'is_published', 'created_at']
    search_fields = ['title', 'description', 'topic__name']
    list_editable = ['is_published', 'order']
    readonly_fields = ['created_at', 'updated_at', 'card_count_display']

    fieldsets = [
        ('Basic Information', {
            'fields': ['topic', 'title', 'description', 'created_by']
        }),
        ('Publication Settings', {
            'fields': ['is_published', 'order']
        }),
        ('Statistics', {
            'fields': ['card_count_display', 'created_at', 'updated_at'],
            'classes': ['collapse']
        })
    ]

    inlines = [FlashcardInline]

    def card_count_display(self, obj):
        count = obj.card_count()
        if count == 0:
            return format_html('<span style="color: #999;">No cards</span>')
        return format_html('<strong>{}</strong> card{}', count, 's' if count != 1 else '')
    card_count_display.short_description = 'Cards'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('topic', 'created_by')

    def save_model(self, request, obj, form, change):
        if not change:  # New object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Flashcard)
class FlashcardAdmin(admin.ModelAdmin):
    list_display = ['flashcard_set', 'order', 'front_preview', 'has_images', 'updated_at']
    list_filter = ['flashcard_set__topic', 'flashcard_set', 'created_at']
    search_fields = ['front_text', 'back_text', 'explanation']
    list_editable = ['order']
    readonly_fields = ['created_at', 'updated_at', 'content_preview']

    fieldsets = [
        ('Card Information', {
            'fields': ['flashcard_set', 'order']
        }),
        ('Front Side (Question)', {
            'fields': ['front_text', 'front_image'],
            'description': 'The question/prompt shown to students. Supports Markdown and LaTeX.'
        }),
        ('Back Side (Correct Answer)', {
            'fields': ['back_text', 'back_image'],
            'description': 'The correct answer. Supports Markdown and LaTeX.'
        }),
        ('Distractors (Incorrect Options)', {
            'fields': ['distractor_1', 'distractor_2', 'distractor_3'],
            'description': 'Three incorrect options for multiple choice. Supports Markdown and LaTeX.'
        }),
        ('Explanation', {
            'fields': ['explanation'],
            'classes': ['collapse'],
            'description': 'Optional explanation shown after answering'
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

    def front_preview(self, obj):
        preview = obj.front_text[:80]
        if len(obj.front_text) > 80:
            preview += '...'
        return preview
    front_preview.short_description = 'Front'

    def has_images(self, obj):
        icons = []
        if obj.front_image:
            icons.append('🖼️ Front')
        if obj.back_image:
            icons.append('🖼️ Back')
        return ' | '.join(icons) if icons else '-'
    has_images.short_description = 'Images'

    def content_preview(self, obj):
        """Rich preview of card content"""
        html_parts = []

        # Front preview
        html_parts.append(f'''
            <h3 style="color: #667eea;">Front (Question)</h3>
            <div style="padding: 10px; background: #f0f4ff; border-radius: 5px; margin-bottom: 15px;">
                <p>{obj.front_text[:300]}</p>
                {f'<img src="{obj.front_image.url}" style="max-width: 300px; max-height: 200px;" />' if obj.front_image else ''}
            </div>
        ''')

        # Back preview
        html_parts.append(f'''
            <h3 style="color: #10b981;">Back (Correct Answer)</h3>
            <div style="padding: 10px; background: #ecfdf5; border-radius: 5px; margin-bottom: 15px;">
                <p><strong>✓ {obj.back_text[:200]}</strong></p>
                {f'<img src="{obj.back_image.url}" style="max-width: 300px; max-height: 200px;" />' if obj.back_image else ''}
            </div>
        ''')

        # Distractors preview
        html_parts.append(f'''
            <h3 style="color: #ef4444;">Distractors (Incorrect Options)</h3>
            <div style="padding: 10px; background: #fef2f2; border-radius: 5px;">
                <p>✗ {obj.distractor_1[:150]}</p>
                <p>✗ {obj.distractor_2[:150]}</p>
                <p>✗ {obj.distractor_3[:150]}</p>
            </div>
        ''')

        if obj.explanation:
            html_parts.append(f'''
                <h3 style="color: #8b5cf6;">Explanation</h3>
                <div style="padding: 10px; background: #f5f3ff; border-radius: 5px;">
                    <p>{obj.explanation[:200]}</p>
                </div>
            ''')

        return mark_safe(''.join(html_parts))
    content_preview.short_description = 'Content Preview'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('flashcard_set', 'flashcard_set__topic')


@admin.register(FlashcardAttempt)
class FlashcardAttemptAdmin(admin.ModelAdmin):
    list_display = ['student', 'flashcard_set', 'flashcard_preview', 'mastery_badge',
                    'view_count', 'correct_count', 'incorrect_count', 'last_viewed_at']
    list_filter = ['mastery_level', 'flashcard__flashcard_set__topic',
                   'flashcard__flashcard_set', 'last_viewed_at']
    search_fields = ['student__username', 'flashcard__front_text']
    readonly_fields = ['created_at', 'last_viewed_at', 'last_answered_at', 'accuracy']

    fieldsets = [
        ('Student & Card', {
            'fields': ['student', 'flashcard']
        }),
        ('Progress Tracking', {
            'fields': ['view_count', 'correct_count', 'incorrect_count', 'accuracy']
        }),
        ('Mastery', {
            'fields': ['mastery_level', 'last_answer_correct']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'last_viewed_at', 'last_answered_at'],
            'classes': ['collapse']
        })
    ]

    def flashcard_set(self, obj):
        return obj.flashcard.flashcard_set.title
    flashcard_set.short_description = 'Set'
    flashcard_set.admin_order_field = 'flashcard__flashcard_set__title'

    def flashcard_preview(self, obj):
        return obj.flashcard.front_text[:60] + '...' if len(obj.flashcard.front_text) > 60 else obj.flashcard.front_text
    flashcard_preview.short_description = 'Card'

    def mastery_badge(self, obj):
        colors = {
            'new': '#6b7280',
            'learning': '#f59e0b',
            'know': '#10b981',
            'dont_know': '#ef4444'
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            colors.get(obj.mastery_level, '#999'),
            obj.get_mastery_level_display()
        )
    mastery_badge.short_description = 'Mastery'

    def accuracy(self, obj):
        total = obj.correct_count + obj.incorrect_count
        if total == 0:
            return '-'
        pct = (obj.correct_count / total) * 100
        return f"{pct:.1f}% ({obj.correct_count}/{total})"
    accuracy.short_description = 'Accuracy'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'student', 'flashcard', 'flashcard__flashcard_set', 'flashcard__flashcard_set__topic'
        )
