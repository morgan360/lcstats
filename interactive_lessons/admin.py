from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.db import models
from django.forms import Textarea

from .models import Topic, Section, Question, QuestionPart, StudentInquiry


# --- Topic Admin --------------------------------------------------------------

@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ["name", "subject", "slug"]
    list_filter = ["subject"]
    search_fields = ["name"]
    readonly_fields = ["slug"]

    fieldsets = (
        ("Basic Information", {
            "fields": ("subject", "name", "slug")
        }),
    )


# --- Section Admin ------------------------------------------------------------

@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ["name", "topic", "order", "question_count"]
    list_editable = ["order"]
    list_filter = ["topic__subject", "topic"]
    search_fields = ["name", "topic__name"]
    ordering = ["topic__subject", "topic__name", "order"]
    readonly_fields = ["slug", "question_count"]

    fieldsets = (
        ("Basic Information", {
            "fields": ("name", "slug", "topic", "order")
        }),
        ("Statistics", {
            "fields": ("question_count",),
            "classes": ("collapse",)
        }),
    )

    def question_count(self, obj):
        """Display the number of questions in this section"""
        return obj.questions.count()
    question_count.short_description = "Questions"


# --- Inline QuestionPart Admin -------------------------------------------------

class QuestionPartInline(admin.StackedInline):
    model = QuestionPart
    extra = 1
    show_change_link = True

    fields = (
        "order",
        "label",
        "prompt",
        "image",
        "answer",
        "expected_format",
        "solution",
        "solution_image",
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
        "question_id_display",
        "topic",
        "order",
        "section",
        "copyright_badge",
        "has_image_indicator",
        "has_solution_indicator",
        "parts_count",
    )
    list_editable = ["section", "order"]
    list_select_related = ("topic", "section")
    list_filter = (
        "topic",
        "section",
        "is_copyrighted",
    )
    search_fields = ("id", "hint", "source_pdf_name", "topic__name", "section__name")
    ordering = ("topic__name", "section__order", "order")
    save_on_top = True
    list_per_page = 50  # Pagination for better performance

    # Add actions for bulk operations
    actions = ['duplicate_questions']

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Customize the section dropdown to show only section names"""
        if db_field.name == "section":
            # Get the topic from the request if editing an existing question
            obj_id = request.resolver_match.kwargs.get('object_id')
            if obj_id:
                try:
                    from .models import Question
                    question = Question.objects.get(pk=obj_id)
                    # Filter sections by the question's topic
                    kwargs["queryset"] = Section.objects.filter(topic=question.topic).order_by('order')
                except:
                    pass
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    fieldsets = (
        ("Basic Information", {
            "fields": ("topic", "order", "section", "is_copyrighted", "is_quickkick_suitable")
        }),
        ("Question Content", {
            "fields": ("hint", "image", "image_url")
        }),
        ("⚠️ DEPRECATED - Question-Level Solution", {
            "fields": ("solution", "solution_image"),
            "classes": ("collapse",),
            "description": "⚠️ These fields are deprecated. Use QuestionPart solution fields instead (in the inline editor below)."
        }),
        ("DEPRECATED - Exam Paper Metadata", {
            "fields": ("is_exam_question", "exam_year", "paper_type", "source_pdf_name"),
            "classes": ("collapse",),
            "description": "⚠️ These fields are deprecated. Use the exam_papers app for exam questions instead."
        }),
    )

    inlines = [QuestionPartInline]

    def get_queryset(self, request):
        """Optimize queryset with prefetch_related to reduce database queries"""
        qs = super().get_queryset(request)
        return qs.select_related('topic', 'section').prefetch_related('parts')

    # --- Copyright Badge Display ----------------------------------------------

    def copyright_badge(self, obj):
        """Display copyright status as a badge."""
        if obj.is_copyrighted:
            return format_html(
                '<span style="background:#FF5722;color:white;padding:2px 8px;'
                'border-radius:3px;font-size:11px;font-weight:bold;">'
                '©️ Copyrighted</span>'
            )
        return format_html(
            '<span style="background:#4CAF50;color:white;padding:2px 8px;'
            'border-radius:3px;font-size:11px;font-weight:bold;">'
            '✓ Original</span>'
        )
    copyright_badge.short_description = "Copyright"

    # --- Lightweight indicators (faster than loading images) ------------------

    def has_image_indicator(self, obj):
        """Show icon if question has an image (faster than loading thumbnails)"""
        if obj.image or obj.image_url:
            return format_html('✅')
        return "-"
    has_image_indicator.short_description = "Image"

    def has_solution_indicator(self, obj):
        """Show icon if question has a solution (faster than loading thumbnails)"""
        if obj.solution or obj.solution_image:
            return format_html('✅')
        return "-"
    has_solution_indicator.short_description = "Solution"

    def question_id_display(self, obj):
        """Display question ID for easy reference and searching"""
        return f"#{obj.id}"
    question_id_display.short_description = "ID"
    question_id_display.admin_order_field = "id"

    def parts_count(self, obj):
        """Show number of question parts"""
        # Use prefetched parts to avoid extra queries
        return obj.parts.count() if hasattr(obj, 'parts') else 0
    parts_count.short_description = "Parts"

    def section_name_only(self, obj):
        """Display only the section name without topic prefix"""
        if obj.section:
            return obj.section.name
        return "-"
    section_name_only.short_description = "Section"
    section_name_only.admin_order_field = "section__order"

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


# --- Student Inquiry Admin ----------------------------------------------------

@admin.register(StudentInquiry)
class StudentInquiryAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "subject",
        "question_link",
        "status_badge",
        "created_at",
        "replied_at",
    )
    list_filter = ("status", "created_at", "replied_at")
    search_fields = (
        "student__username",
        "student__email",
        "student__first_name",
        "student__last_name",
        "subject",
        "message",
    )
    readonly_fields = (
        "student",
        "question",
        "subject",
        "message",
        "topic_name",
        "question_number",
        "section_name",
        "created_at",
        "student_email",
        "inquiry_details",
    )
    ordering = ("-created_at",)
    date_hierarchy = "created_at"

    fieldsets = (
        ("Student Inquiry", {
            "fields": ("inquiry_details", "student_email", "created_at")
        }),
        ("Teacher Reply", {
            "fields": ("reply", "status", "replied_at"),
            "classes": ("wide",)
        }),
    )

    def student_email(self, obj):
        """Display student's email for easy reference"""
        return obj.student.email
    student_email.short_description = "Student Email"

    def inquiry_details(self, obj):
        """Display the full inquiry in a readable format"""
        details = f"""
        <div style="background:#f9f9f9; padding:15px; border-radius:5px; border-left:4px solid #4CAF50;">
            <p><strong>From:</strong> {obj.student.get_full_name() or obj.student.username}</p>
            <p><strong>Topic:</strong> {obj.topic_name or 'N/A'}</p>
            <p><strong>Question:</strong> {obj.question_number or 'N/A'}</p>
            {f'<p><strong>Section:</strong> {obj.section_name}</p>' if obj.section_name else ''}
            <p><strong>Subject:</strong> {obj.subject}</p>
            <p><strong>Message:</strong></p>
            <div style="background:white; padding:10px; border-radius:3px; white-space:pre-wrap;">
{obj.message}
            </div>
        </div>
        """
        return format_html(details)
    inquiry_details.short_description = "Student Inquiry Details"

    def question_link(self, obj):
        """Link to the question in admin"""
        if obj.question:
            url = reverse("admin:interactive_lessons_question_change", args=[obj.question.id])
            return format_html('<a href="{}">{} - Q{}</a>', url, obj.topic_name, obj.question.order)
        return "-"
    question_link.short_description = "Question"

    def status_badge(self, obj):
        """Display status as a colored badge"""
        if obj.status == 'answered':
            color = '#4CAF50'
            text = 'Answered'
        else:
            color = '#FF9800'
            text = 'Unanswered'
        return format_html(
            '<span style="background:{};color:white;padding:3px 10px;'
            'border-radius:3px;font-size:11px;font-weight:bold;">{}</span>',
            color, text
        )
    status_badge.short_description = "Status"

    def save_model(self, request, obj, form, change):
        """Send email to student when reply is added"""
        from django.core.mail import send_mail
        from django.conf import settings
        from django.utils import timezone

        # Check if reply was just added
        if change and 'reply' in form.changed_data and obj.reply:
            obj.status = 'answered'
            obj.replied_at = timezone.now()

            # Send email to student
            email_subject = f"Re: {obj.subject}"
            email_body = f"""
Hello {obj.student.get_full_name() or obj.student.username},

Thank you for your question about {obj.topic_name} - {obj.question_number}.

Your original message:
{obj.message}

---

Teacher's Reply:
{obj.reply}

---

If you have any further questions, please don't hesitate to ask!

Best regards,
LCAI Maths
            """

            try:
                send_mail(
                    subject=email_subject,
                    message=email_body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[obj.student.email],
                    fail_silently=False,
                )
                self.message_user(request, f"✅ Reply sent to {obj.student.username} via email!")
            except Exception as e:
                self.message_user(
                    request,
                    f"⚠️ Reply saved but email failed to send: {e}",
                    level='warning'
                )

        super().save_model(request, obj, form, change)
