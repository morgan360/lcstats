from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import StudentProfile, QuestionAttempt, RegistrationCode, LoginHistory, UserSession


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'total_score', 'lessons_completed', 'last_activity')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('last_activity',)


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
    readonly_fields = ('user', 'session', 'ip_address', 'user_agent', 'login_time', 'last_activity')
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
        count = 0
        for user_session in queryset:
            try:
                user_session.session.delete()
                count += 1
            except:
                pass
        self.message_user(request, f"{count} session(s) terminated.")
    terminate_sessions.short_description = "Terminate selected sessions"
