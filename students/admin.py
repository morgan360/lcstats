from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.http import HttpResponse
from django.db.models import Count, Avg, Q
from datetime import timedelta
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from .models import StudentProfile, QuestionAttempt, RegistrationCode, LoginHistory, UserSession


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'total_score', 'lessons_completed', 'last_activity')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('last_activity',)
    actions = ['generate_daily_report', 'generate_weekly_report', 'generate_monthly_report', 'generate_yearly_report']

    def _generate_report(self, request, queryset, days=1):
        """Helper method to generate activity report as PDF"""
        # Calculate date range
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)

        # Get attempts in the date range, excluding the admin user
        attempts_in_period = QuestionAttempt.objects.filter(
            attempted_at__gte=start_date,
            attempted_at__lte=end_date
        ).exclude(student__user=request.user).select_related('student__user', 'question__topic')

        # If specific students selected, filter to those
        if queryset.exists():
            attempts_in_period = attempts_in_period.filter(student__in=queryset)

        # Get students to report
        students_to_report = queryset if queryset.exists() else StudentProfile.objects.exclude(user=request.user)

        # Create PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()

        # Title
        title = Paragraph(f"<b>Student Question Attempts Report ({days} Day{'s' if days > 1 else ''})</b>", styles['Heading1'])
        elements.append(title)
        elements.append(Spacer(1, 12))

        # Generate report for each student
        for student in students_to_report:
            student_attempts = attempts_in_period.filter(student=student).order_by('question__topic__name', '-attempted_at')

            if student_attempts.count() == 0:
                continue

            # Student name
            student_name = Paragraph(f"<b>{student.user.get_full_name() or student.user.username}</b>", styles['Heading2'])
            elements.append(student_name)
            elements.append(Spacer(1, 6))

            # Group by topic
            current_topic = None
            topic_data = []

            for attempt in student_attempts:
                topic_name = attempt.question.topic.name if attempt.question.topic else 'No Topic'

                if current_topic != topic_name:
                    # Add previous topic's table
                    if topic_data:
                        elements.append(Paragraph(f"<i>{current_topic}</i>", styles['Heading3']))
                        elements.append(Spacer(1, 4))

                        table = Table(topic_data, colWidths=[90, 70, 270])
                        table.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                            ('FONTSIZE', (0, 0), (-1, 0), 9),
                            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                            ('GRID', (0, 0), (-1, -1), 1, colors.black)
                        ]))
                        elements.append(table)
                        elements.append(Spacer(1, 10))

                    # Start new topic
                    current_topic = topic_name
                    topic_data = [['Date', 'Result', 'Question']]

                # Add attempt
                date_str = attempt.attempted_at.strftime('%Y-%m-%d %H:%M')
                result = 'Correct' if attempt.is_correct else 'Wrong'
                question_text = attempt.question.text[:55] + '...' if len(attempt.question.text) > 55 else attempt.question.text
                topic_data.append([date_str, result, question_text])

            # Add final topic's table
            if topic_data and len(topic_data) > 1:
                elements.append(Paragraph(f"<i>{current_topic}</i>", styles['Heading3']))
                elements.append(Spacer(1, 4))

                table = Table(topic_data, colWidths=[90, 70, 270])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                elements.append(table)

            elements.append(Spacer(1, 20))

        # Build PDF
        doc.build(elements)
        buffer.seek(0)

        # Return as downloadable PDF
        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        filename = f'student_report_{days}day_{end_date.strftime("%Y%m%d")}.pdf'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    def generate_daily_report(self, request, queryset):
        """Generate a report for the last 24 hours"""
        return self._generate_report(request, queryset, days=1)
    generate_daily_report.short_description = "📊 Generate Daily Report (24 hours)"

    def generate_weekly_report(self, request, queryset):
        """Generate a report for the last 7 days"""
        return self._generate_report(request, queryset, days=7)
    generate_weekly_report.short_description = "📊 Generate Weekly Report (7 days)"

    def generate_monthly_report(self, request, queryset):
        """Generate a report for the last 30 days"""
        return self._generate_report(request, queryset, days=30)
    generate_monthly_report.short_description = "📊 Generate Monthly Report (30 days)"

    def generate_yearly_report(self, request, queryset):
        """Generate a report for the last 365 days"""
        return self._generate_report(request, queryset, days=365)
    generate_yearly_report.short_description = "📊 Generate Yearly Report (365 days)"


@admin.register(QuestionAttempt)
class QuestionAttemptAdmin(admin.ModelAdmin):
    list_display = ('student', 'question', 'question_part', 'score_awarded', 'is_correct', 'attempted_at')
    list_filter = ('is_correct', 'attempted_at')
    search_fields = ('student__user__username', 'question__id')
    readonly_fields = ('attempted_at', 'marks_awarded')


@admin.register(RegistrationCode)
class RegistrationCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'is_active', 'times_used', 'max_uses', 'description', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('code', 'description')
    readonly_fields = ('times_used', 'created_at')

    fieldsets = (
        ('Code Information', {
            'fields': ('code', 'description')
        }),
        ('Usage Settings', {
            'fields': ('is_active', 'max_uses', 'times_used')
        }),
        ('Metadata', {
            'fields': ('created_at', 'created_by')
        }),
    )

    actions = ['deactivate_codes', 'activate_codes']

    def deactivate_codes(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f"{queryset.count()} code(s) deactivated.")
    deactivate_codes.short_description = "Deactivate selected codes"

    def activate_codes(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f"{queryset.count()} code(s) activated.")
    activate_codes.short_description = "Activate selected codes"


@admin.register(LoginHistory)
class LoginHistoryAdmin(admin.ModelAdmin):
    list_display = ('status_icon', 'username_attempted', 'user_link', 'timestamp', 'ip_address', 'short_user_agent')
    list_filter = ('success', 'timestamp')
    search_fields = ('username_attempted', 'user__username', 'ip_address')
    readonly_fields = ('user', 'username_attempted', 'timestamp', 'success', 'ip_address', 'user_agent', 'session_key')
    date_hierarchy = 'timestamp'

    def has_add_permission(self, request):
        # Prevent manual creation - should only be created by signals
        return False

    def has_change_permission(self, request, obj=None):
        # Make records read-only
        return False

    def status_icon(self, obj):
        if obj.success:
            return format_html('<span style="color: green; font-size: 16px;">✓</span>')
        return format_html('<span style="color: red; font-size: 16px;">✗</span>')
    status_icon.short_description = 'Status'

    def user_link(self, obj):
        if obj.user:
            return format_html('<a href="/admin/auth/user/{}/change/">{}</a>', obj.user.id, obj.user.username)
        return '-'
    user_link.short_description = 'User'

    def short_user_agent(self, obj):
        if len(obj.user_agent) > 50:
            return obj.user_agent[:50] + '...'
        return obj.user_agent
    short_user_agent.short_description = 'Browser/Device'


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ('user_link', 'login_time', 'last_activity', 'time_active', 'ip_address', 'short_user_agent', 'is_active_display')
    list_filter = ('login_time', 'last_activity')
    search_fields = ('user__username', 'ip_address')
    readonly_fields = ('user', 'session_key', 'ip_address', 'user_agent', 'login_time', 'last_activity')
    date_hierarchy = 'login_time'

    def has_add_permission(self, request):
        # Prevent manual creation - should only be created by signals
        return False

    def has_change_permission(self, request, obj=None):
        # Make records read-only
        return False

    def user_link(self, obj):
        return format_html('<a href="/admin/auth/user/{}/change/">{}</a>', obj.user.id, obj.user.username)
    user_link.short_description = 'User'

    def time_active(self, obj):
        duration = timezone.now() - obj.login_time
        hours = duration.total_seconds() // 3600
        minutes = (duration.total_seconds() % 3600) // 60
        if hours > 0:
            return f"{int(hours)}h {int(minutes)}m"
        return f"{int(minutes)}m"
    time_active.short_description = 'Duration'

    def is_active_display(self, obj):
        if obj.is_active():
            return format_html('<span style="color: green;">●</span> Active')
        return format_html('<span style="color: gray;">○</span> Expired')
    is_active_display.short_description = 'Status'

    def short_user_agent(self, obj):
        if len(obj.user_agent) > 50:
            return obj.user_agent[:50] + '...'
        return obj.user_agent
    short_user_agent.short_description = 'Browser/Device'

    actions = ['terminate_sessions']

    def terminate_sessions(self, request, queryset):
        from django.contrib.sessions.models import Session
        count = 0
        for user_session in queryset:
            try:
                session = Session.objects.get(session_key=user_session.session_key)
                session.delete()
                count += 1
            except Session.DoesNotExist:
                pass
        self.message_user(request, f"{count} session(s) terminated.")
    terminate_sessions.short_description = "Terminate selected sessions"
