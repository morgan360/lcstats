from django.contrib import admin
from .models import StudentProfile, QuestionAttempt, RegistrationCode


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
