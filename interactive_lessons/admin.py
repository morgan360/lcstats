from django.contrib import admin
from .models import Topic, Question
from django.utils.html import format_html

@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ["name"]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("topic", "order", "section", "preview_image")
    fields = (
        "topic", "order", "section", "text", "image", "image_url",
        "answer", "hint", "solution"
    )

    def preview_image(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height:60px;">', obj.image.url)
        elif obj.image_url:
            return format_html('<img src="{}" style="max-height:60px;">', obj.image_url)
        return "-"
    preview_image.short_description = "Preview"
