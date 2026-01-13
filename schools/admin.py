from django.contrib import admin
from django.shortcuts import render, redirect
from django.urls import path
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from django.conf import settings
from .models import School, EmailLog
from .forms import SendEmailForm


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    """Admin interface for School model with outreach tracking."""

    list_display = [
        'name',
        'county',
        'principal_name',
        'email',
        'phone',
        'school_type',
        'initial_email_sent',
        'response_received',
        'interested',
        'follow_up_required',
    ]

    list_filter = [
        'county',
        'school_type',
        'response_received',
        'interested',
        'follow_up_required',
        'initial_email_sent',
    ]

    search_fields = [
        'name',
        'principal_name',
        'email',
        'county',
        'address',
        'roll_number',
    ]

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'principal_name', 'email', 'phone', 'website')
        }),
        ('Location', {
            'fields': ('address', 'county')
        }),
        ('School Details', {
            'fields': ('school_type', 'roll_number')
        }),
        ('Outreach Tracking', {
            'fields': (
                'initial_email_sent',
                'response_received',
                'response_date',
                'follow_up_required',
                'follow_up_date',
                'interested',
            )
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['created_at', 'updated_at']

    date_hierarchy = 'initial_email_sent'

    list_per_page = 50

    actions = ['send_email_action', 'mark_as_contacted', 'mark_as_responded', 'mark_for_follow_up']

    def get_urls(self):
        """Add custom URL for email sending page."""
        urls = super().get_urls()
        custom_urls = [
            path('send-email/', self.admin_site.admin_view(self.send_email_view), name='schools_school_send_email'),
        ]
        return custom_urls + urls

    def send_email_action(self, request, queryset):
        """Admin action to send emails to selected schools."""
        # Store selected school IDs in session
        selected = queryset.values_list('id', flat=True)
        request.session['schools_to_email'] = list(selected)
        return redirect('admin:schools_school_send_email')
    send_email_action.short_description = "Send email to selected schools"

    def send_email_view(self, request):
        """View for composing and sending emails."""
        school_ids = request.session.get('schools_to_email', [])
        schools = School.objects.filter(id__in=school_ids)

        if request.method == 'POST':
            form = SendEmailForm(request.POST)
            if form.is_valid():
                success_count = 0
                error_count = 0

                subject = form.cleaned_data['subject']
                email_type = form.cleaned_data['email_type']
                use_template = form.cleaned_data['use_template']
                custom_message = form.cleaned_data['custom_message']
                send_test = form.cleaned_data['send_test']

                # Determine recipients
                if send_test:
                    # Send test email to current user
                    test_schools = [schools.first()] if schools.exists() else []
                    recipient_email = request.user.email or settings.TEACHER_EMAIL
                else:
                    test_schools = schools
                    recipient_email = None

                for school in test_schools:
                    try:
                        # Prepare context for template
                        context = {
                            'principal_name': school.principal_name,
                            'school_name': school.name,
                        }

                        # Generate email body
                        if use_template:
                            body_html = render_to_string('schools/emails/initial_outreach.html', context)
                            body_text = render_to_string('schools/emails/initial_outreach.txt', context)
                        else:
                            body_text = custom_message
                            body_html = None

                        # Create email
                        to_email = recipient_email if send_test else school.email
                        email = EmailMultiAlternatives(
                            subject=subject,
                            body=body_text,
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            to=[to_email],
                            reply_to=[settings.TEACHER_EMAIL],
                        )

                        if body_html:
                            email.attach_alternative(body_html, "text/html")

                        # Send email
                        email.send()

                        # Log the email
                        EmailLog.objects.create(
                            school=school,
                            email_type=email_type,
                            subject=subject,
                            body_text=body_text,
                            body_html=body_html or '',
                            sent_to=to_email,
                            sent_by=request.user,
                            status='sent'
                        )

                        # Update school if not test email
                        if not send_test and email_type == 'initial':
                            school.initial_email_sent = timezone.now()
                            school.save()

                        success_count += 1

                    except Exception as e:
                        # Log the error
                        EmailLog.objects.create(
                            school=school,
                            email_type=email_type,
                            subject=subject,
                            body_text=body_text if 'body_text' in locals() else '',
                            body_html=body_html if 'body_html' in locals() else '',
                            sent_to=to_email if 'to_email' in locals() else school.email,
                            sent_by=request.user,
                            status='failed',
                            error_message=str(e)
                        )
                        error_count += 1

                # Show success message
                if send_test:
                    self.message_user(request, f"Test email sent to {recipient_email}")
                else:
                    msg = f"Successfully sent {success_count} email(s)."
                    if error_count > 0:
                        msg += f" {error_count} email(s) failed."
                    self.message_user(request, msg)

                # Clear session and redirect
                if 'schools_to_email' in request.session:
                    del request.session['schools_to_email']
                return redirect('admin:schools_school_changelist')
        else:
            form = SendEmailForm()

        context = {
            'form': form,
            'schools': schools,
            'schools_count': schools.count(),
            'opts': self.model._meta,
            'has_view_permission': self.has_view_permission(request),
            'site_title': admin.site.site_title,
            'site_header': admin.site.site_header,
        }

        return render(request, 'admin/schools/send_email.html', context)

    def mark_as_contacted(self, request, queryset):
        """Mark selected schools as contacted."""
        from django.utils import timezone
        updated = queryset.update(initial_email_sent=timezone.now())
        self.message_user(request, f"{updated} school(s) marked as contacted.")
    mark_as_contacted.short_description = "Mark selected as contacted"

    def mark_as_responded(self, request, queryset):
        """Mark selected schools as having responded."""
        from django.utils import timezone
        updated = queryset.update(response_received=True, response_date=timezone.now())
        self.message_user(request, f"{updated} school(s) marked as responded.")
    mark_as_responded.short_description = "Mark selected as responded"

    def mark_for_follow_up(self, request, queryset):
        """Mark selected schools for follow-up."""
        updated = queryset.update(follow_up_required=True)
        self.message_user(request, f"{updated} school(s) marked for follow-up.")
    mark_for_follow_up.short_description = "Mark selected for follow-up"


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    """Admin interface for EmailLog model."""

    list_display = [
        'school',
        'email_type',
        'subject',
        'sent_to',
        'sent_by',
        'sent_at',
        'status',
    ]

    list_filter = [
        'email_type',
        'status',
        'sent_at',
    ]

    search_fields = [
        'school__name',
        'subject',
        'sent_to',
        'body_text',
    ]

    readonly_fields = [
        'school',
        'email_type',
        'subject',
        'body_text',
        'body_html',
        'sent_to',
        'sent_by',
        'sent_at',
        'status',
        'error_message',
        'created_at',
    ]

    fieldsets = (
        ('Email Details', {
            'fields': ('school', 'email_type', 'subject', 'sent_to')
        }),
        ('Email Body', {
            'fields': ('body_text', 'body_html'),
            'classes': ('collapse',)
        }),
        ('Sending Information', {
            'fields': ('sent_by', 'sent_at', 'status', 'error_message')
        }),
    )

    date_hierarchy = 'sent_at'

    list_per_page = 50

    def has_add_permission(self, request):
        """Prevent manual creation of email logs."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of email logs for audit trail."""
        return False
