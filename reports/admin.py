from django.contrib import admin

from .models import (
    ClassSession,
    ClassTest,
    CommentPreset,
    CreditBalance,
    StudentClassNote,
    StudentSessionRecord,
    TestResult,
    TimetableSlot,
)


@admin.register(CommentPreset)
class CommentPresetAdmin(admin.ModelAdmin):
    list_display = ('text', 'category', 'tone', 'order', 'is_active')
    list_editable = ('order', 'is_active')
    list_filter = ('category', 'tone', 'is_active')
    search_fields = ('text',)


@admin.register(TimetableSlot)
class TimetableSlotAdmin(admin.ModelAdmin):
    list_display = ('teacher_class', 'weekday', 'start_time', 'label', 'is_active')
    list_filter = ('teacher_class', 'weekday')
    list_editable = ('is_active',)


class StudentSessionRecordInline(admin.TabularInline):
    model = StudentSessionRecord
    raw_id_fields = ('student',)
    extra = 0


@admin.register(ClassSession)
class ClassSessionAdmin(admin.ModelAdmin):
    list_display = ('teacher_class', 'date', 'slot', 'homework_due')
    list_filter = ('teacher_class', 'homework_due')
    date_hierarchy = 'date'
    inlines = [StudentSessionRecordInline]


class TestResultInline(admin.TabularInline):
    model = TestResult
    raw_id_fields = ('student',)
    extra = 0


@admin.register(ClassTest)
class ClassTestAdmin(admin.ModelAdmin):
    list_display = ('name', 'teacher_class', 'date', 'max_marks')
    list_filter = ('teacher_class',)
    date_hierarchy = 'date'
    inlines = [TestResultInline]


@admin.register(StudentClassNote)
class StudentClassNoteAdmin(admin.ModelAdmin):
    list_display = ('student', 'teacher_class', 'ability', 'note', 'updated_at')
    list_filter = ('teacher_class', 'ability')
    search_fields = ('student__username', 'student__first_name', 'student__last_name', 'note')
    raw_id_fields = ('student',)


@admin.register(CreditBalance)
class CreditBalanceAdmin(admin.ModelAdmin):
    """History only. New balances go in on the AI spend page, which also notes
    the OpenAI spend already taken off, so there is no Add button here."""
    list_display = ('provider', 'amount', 'recorded_at', 'spend_already_counted', 'recorded_by')
    list_filter = ('provider',)
    readonly_fields = ('provider', 'amount', 'recorded_at', 'spend_already_counted', 'recorded_by')

    def has_add_permission(self, request):
        return False
