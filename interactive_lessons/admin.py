from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.db import models
from django.forms import Textarea

from .models import Topic, Question, QuestionPart


# --- Topic Admin --------------------------------------------------------------

@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ["name"]
    search_fields = ["name"]


# --- Inline QuestionPart Admin -------------------------------------------------

class QuestionPartInline(admin.StackedInline):
    model = QuestionPart
    extra = 1
    show_change_link = True

    fields = (
        "order",
        "label",
        "prompt",
        "answer",
        "hint",
        "expected_type",
        "scale",
        "max_marks",
    )

    # ✅ Make text boxes smaller for compact editing
    formfield_overrides = {
        models.TextField: {"widget": Textarea(attrs={"rows": 2, "cols": 70})},
    }


# --- Question Admin -----------------------------------------------------------

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = (
        "topic",
        "order",
        "section",
        "preview_image",
        "preview_solution_image",
    )
    list_editable = ["section", "order"]
    list_select_related = ("topic",)
    list_filter = ("topic", "section")
    search_fields = ("text", "section")
    ordering = ("topic__name", "order")
    save_on_top = True

    fields = (
        "topic",
        "order",
        "section",
        "text",
        "solution",
        "image",
        "image_url",
        "solution_image",
    )

    inlines = [QuestionPartInline]

    # --- Image previews -------------------------------------------------------

    def preview_image(self, obj):
        """Thumbnail preview for the question image."""
        if obj.image:
            return format_html('<img src="{}" style="max-height:60px;">', obj.image.url)
        elif obj.image_url:
            return format_html('<img src="{}" style="max-height:60px;">', obj.image_url)
        return "-"
    preview_image.short_description = "Question Image"

    def preview_solution_image(self, obj):
        """Thumbnail preview for the solution image."""
        if obj.solution_image:
            return format_html('<img src="{}" style="max-height:60px;">', obj.solution_image.url)
        return "-"
    preview_solution_image.short_description = "Solution Image"

    # --- Custom Save + Next Navigation ----------------------------------------

    def response_change(self, request, obj):
        """Handle the custom 'Save and Next' button to stay in workflow."""
        if "_saveandnext" in request.POST:
            try:
                next_id = int(request.POST.get("_saveandnext"))
                url = reverse("admin:interactive_lessons_question_change", args=[next_id])
                self.message_user(request, "✅ Saved — moving to next question…")
                return HttpResponseRedirect(url)
            except Exception:
                self.message_user(request, "✅ Saved, but no next question found.")
                return super().response_change(request, obj)
        return super().response_change(request, obj)
