from django.contrib import admin

from .models import (
    StudyPlan, StudyPlanCheckpoint, StudyPlanCheckpointPart, StudyPlanEvent,
    StudyPlanGoal, StudyPlanItem, StudyPlanWeek,
)


class StudyPlanGoalInline(admin.TabularInline):
    model = StudyPlanGoal
    extra = 1
    fields = ('topic', 'target_mastery', 'checkpoint_size', 'priority', 'order',
              'mastered_at', 'mastery_score')
    readonly_fields = ('mastered_at', 'mastery_score')
    autocomplete_fields = ('topic',)


class StudyPlanWeekInline(admin.TabularInline):
    model = StudyPlanWeek
    extra = 0
    fields = ('index', 'start_date', 'end_date', 'minutes_budget', 'focus_note')


@admin.register(StudyPlan)
class StudyPlanAdmin(admin.ModelAdmin):
    list_display = ('title', 'student', 'subject', 'status', 'start_date',
                    'deadline', 'mastered_display')
    list_filter = ('status', 'subject', 'is_locked')
    search_fields = ('title', 'student__username', 'student__first_name',
                     'student__last_name')
    date_hierarchy = 'start_date'
    inlines = [StudyPlanGoalInline, StudyPlanWeekInline]
    readonly_fields = ('last_checked_at', 'created_at', 'updated_at')

    @admin.display(description="Mastered")
    def mastered_display(self, obj):
        done, total = obj.goal_progress()
        return f"{done}/{total}"


class StudyPlanCheckpointPartInline(admin.TabularInline):
    model = StudyPlanCheckpointPart
    extra = 0
    fields = ('order', 'exam_question_part', 'marks_possible', 'marks_awarded',
              'score', 'attempted_at', 'hint_used', 'solution_viewed')
    readonly_fields = ('marks_awarded', 'score', 'attempted_at', 'hint_used',
                       'solution_viewed')


@admin.register(StudyPlanCheckpoint)
class StudyPlanCheckpointAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'status', 'round', 'pass_mark', 'score',
                    'is_clean', 'sat_at')
    list_filter = ('status', 'is_clean')
    search_fields = ('goal__topic__name', 'goal__plan__student__username')
    inlines = [StudyPlanCheckpointPartInline]
    readonly_fields = ('marks_awarded', 'marks_possible', 'score', 'sat_at',
                       'created_at')


@admin.register(StudyPlanGoal)
class StudyPlanGoalAdmin(admin.ModelAdmin):
    list_display = ('topic', 'plan', 'target_mastery', 'mastery_score',
                    'mastered_at', 'needs_teacher_attention')
    list_filter = ('needs_teacher_attention', 'priority', 'topic__subject')
    search_fields = ('topic__name', 'plan__student__username')


@admin.register(StudyPlanItem)
class StudyPlanItemAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'content_type', 'status', 'origin', 'week',
                    'estimated_minutes', 'due_date')
    list_filter = ('status', 'origin', 'content_type', 'needs_teacher_attention')
    search_fields = ('plan__title', 'plan__student__username', 'instructions')
    readonly_fields = ('started_at', 'completed_at', 'evidence_score',
                       'evidence_note', 'carried_over_count')


@admin.register(StudyPlanWeek)
class StudyPlanWeekAdmin(admin.ModelAdmin):
    list_display = ('plan', 'index', 'start_date', 'end_date', 'minutes_budget')
    list_filter = ('plan__status',)


@admin.register(StudyPlanEvent)
class StudyPlanEventAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'plan', 'kind', 'message')
    list_filter = ('kind',)
    search_fields = ('plan__title', 'message')
    readonly_fields = ('plan', 'kind', 'message', 'item', 'checkpoint', 'created_at')
