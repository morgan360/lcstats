from django.contrib import admin
from django.shortcuts import render
from django.urls import path
from django import forms
from .models import Note, InfoBotQuery, InfoBotFeedback
from .utils import search_similar


# ---------- Simple search form ----------
class SearchForm(forms.Form):
    query = forms.CharField(label="Search Notes", max_length=200)


# ---------- Basic NoteAdmin ----------
@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ("title", "topic")
    search_fields = ("title", "content")
    exclude = ("embedding",)

    # Optional semantic search template
    change_list_template = "admin/notes/change_list_with_search.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "semantic-search/",
                self.admin_site.admin_view(self.semantic_search_view),
                name="notes_semantic_search",
            ),
        ]
        return custom_urls + urls

    def semantic_search_view(self, request):
        form = SearchForm(request.GET or None)
        results = []

        if form.is_valid():
            query = form.cleaned_data["query"]
            results = search_similar(query)

        context = {
            **self.admin_site.each_context(request),
            "form": form,
            "results": results,
            "title": "Semantic Note Search",
        }
        return render(request, "admin/notes/semantic_search.html", context)


# ---------- InfoBotQuery Admin ----------
@admin.register(InfoBotQuery)
class InfoBotQueryAdmin(admin.ModelAdmin):
    list_display = ("created_at", "topic_slug", "source_type", "confidence", "short_question", "short_answer")
    list_filter = ("topic_slug", "source_type")
    search_fields = ("question", "answer", "sources")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "question", "answer", "confidence", "sources", "source_type", "topic_slug")

    def has_module_permission(self, request):
        """Only superusers can access InfoBot queries"""
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        """Only superusers can view InfoBot queries"""
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        """Only superusers can change InfoBot queries"""
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        """Only superusers can delete InfoBot queries"""
        return request.user.is_superuser

    def short_question(self, obj):
        return (obj.question[:80] + "…") if len(obj.question) > 80 else obj.question
    short_question.short_description = "Question"

    def short_answer(self, obj):
        if not obj.answer:
            return "(no answer)"
        return (obj.answer[:100] + "…") if len(obj.answer) > 100 else obj.answer
    short_answer.short_description = "Answer"

    # Optional: color-code confidence for quick visual scanning
    def confidence_display(self, obj):
        if obj.confidence is None:
            return "-"
        if obj.confidence >= 0.8:
            color = "#4CAF50"  # green
        elif obj.confidence >= 0.5:
            color = "#FFC107"  # amber
        else:
            color = "#F44336"  # red
        return format_html('<span style="color:{};">{:.2f}</span>', color, obj.confidence)
    confidence_display.short_description = "Confidence"


# ---------- InfoBotFeedback Admin ----------
@admin.register(InfoBotFeedback)
class InfoBotFeedbackAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "feedback_type", "query_snippet")
    list_filter = ("feedback_type", "created_at")
    search_fields = ("user__username", "query__question")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "user", "query", "feedback_type")

    def has_module_permission(self, request):
        """Only superusers can access feedback"""
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        """Feedback is read-only"""
        return False

    def query_snippet(self, obj):
        question = obj.query.question
        return (question[:60] + "…") if len(question) > 60 else question
    query_snippet.short_description = "Query"
