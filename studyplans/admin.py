from django.contrib import admin

from .models import (
    StudyPlan, StudyPlanCheckpoint, StudyPlanCheckpointPart, StudyPlanEvent,
    StudyPlanGoal, StudyPlanItem, StudyPlanMicroBadge,
)

# StudyPlanWeek is deliberately not registered. Weeks stopped being part of a
# plan when MicroBadges replaced them; the table is kept so no history was
# thrown away, but offering it here only invites building a plan that cannot
# work. Plans are built at /study-plans/teacher/new/ and shaped from the
# manage page -- admin is for looking, and for the occasional repair.


class StudyPlanGoalInline(admin.TabularInline):
    model = StudyPlanGoal
    extra = 1
    fields = ('topic', 'target_mastery', 'checkpoint_size', 'priority', 'order',
              'mastered_at', 'mastery_score')
    readonly_fields = ('mastered_at', 'mastery_score')
    autocomplete_fields = ('topic',)


class StudyPlanMicroBadgeInline(admin.TabularInline):
    model = StudyPlanMicroBadge
    extra = 0
    fields = ('number', 'kind', 'target_date', 'earned_at', 'earned_by_teacher')
    readonly_fields = ('earned_at', 'earned_by_teacher')


@admin.register(StudyPlan)
class StudyPlanAdmin(admin.ModelAdmin):
    list_display = ('title', 'student', 'subject', 'status', 'start_date',
                    'deadline', 'mastered_display')
    list_filter = ('status', 'subject', 'is_locked')
    search_fields = ('title', 'student__username', 'student__first_name',
                     'student__last_name')
    date_hierarchy = 'start_date'
    inlines = [StudyPlanGoalInline]
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
    list_display = ('topic', 'plan', 'badges_display', 'target_mastery',
                    'mastery_score', 'mastered_at', 'needs_teacher_attention')
    list_filter = ('needs_teacher_attention', 'priority', 'topic__subject')
    search_fields = ('topic__name', 'plan__student__username')
    inlines = [StudyPlanMicroBadgeInline]

    @admin.display(description="MicroBadges")
    def badges_display(self, obj):
        badges = [b for b in obj.micro_badges.all() if b.kind == 'core']
        return f"{sum(1 for b in badges if b.earned_at)}/{len(badges)}"


class StudyPlanItemInline(admin.TabularInline):
    model = StudyPlanItem
    extra = 0
    fields = ('order', 'content_type', 'section', 'exam_question_part',
              'quickkick', 'flashcard_set', 'status', 'estimated_minutes')
    readonly_fields = ('status',)
    autocomplete_fields = ('section',)


@admin.register(StudyPlanMicroBadge)
class StudyPlanMicroBadgeAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'kind', 'target_date', 'items_display',
                    'earned_at', 'earned_by_teacher')
    list_filter = ('kind', 'earned_by_teacher', 'goal__topic__subject')
    search_fields = ('goal__topic__name', 'goal__plan__student__username')
    readonly_fields = ('earned_at', 'earned_by_teacher')
    inlines = [StudyPlanItemInline]

    @admin.display(description="Items done")
    def items_display(self, obj):
        items = obj.live_items()
        return f"{sum(1 for i in items if i.status == 'done')}/{len(items)}"


@admin.register(StudyPlanItem)
class StudyPlanItemAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'content_type', 'status', 'origin', 'micro_badge',
                    'estimated_minutes', 'due_date')
    list_filter = ('status', 'origin', 'content_type', 'needs_teacher_attention')
    search_fields = ('plan__title', 'plan__student__username', 'instructions')
    readonly_fields = ('started_at', 'completed_at', 'evidence_score',
                       'evidence_note', 'carried_over_count')
    # `week` is dead weight on a plan built from MicroBadges, and a value in it
    # would say a plan is shaped in a way nothing reads any more.
    exclude = ('week',)


@admin.register(StudyPlanEvent)
class StudyPlanEventAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'plan', 'kind', 'message')
    list_filter = ('kind',)
    search_fields = ('plan__title', 'message')
    readonly_fields = ('plan', 'kind', 'message', 'item', 'checkpoint', 'created_at')
