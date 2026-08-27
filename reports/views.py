import csv
import json
from datetime import datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from io import BytesIO

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.db.models import Avg, Count
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from homework.models import TeacherClass
from students.decorators import teacher_required

from . import services
from .models import (
    ClassSession,
    ClassTest,
    CommentPreset,
    StudentClassNote,
    StudentSessionRecord,
    TestResult,
    TimetableSlot,
)

MIDNIGHT_HEX = '#001C3D'  # tailwind.config.js "midnight" token


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def _get_owned_class(request, class_id):
    teacher_class = get_object_or_404(TeacherClass, id=class_id)
    if request.user.is_superuser:
        return teacher_class
    if teacher_class.teacher != request.user.teacher_profile:
        raise PermissionDenied
    return teacher_class


def _get_owned_student(request, student_id):
    student = get_object_or_404(User, id=student_id)
    if request.user.is_superuser:
        return student
    if not request.user.teacher_profile.classes.filter(students__id=student_id).exists():
        raise PermissionDenied
    return student


def _parse_date(value, default):
    if not value:
        return default
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError:
        return default


def _day_start(d):
    """Timezone-aware datetime at midnight of date d."""
    return timezone.make_aware(datetime.combine(d, time.min))


def _roster(teacher_class):
    return teacher_class.students.all().order_by('first_name', 'last_name', 'username')


def _short_name(user):
    """
    First given name plus the last word of the surname, so long rosters stay
    readable: 'Maria Eduarda Alencar Soares' becomes 'Maria Soares' and
    'Francesca De Oliveira Castelhano Tafuri' becomes 'Francesca Tafuri'.
    Hyphenated surnames are one word and survive whole (Sadolewski-Odinakaeze).
    """
    given = (user.first_name or '').split()
    surname = (user.last_name or '').split()
    name = ' '.join(filter(None, [given[0] if given else '', surname[-1] if surname else ''])).strip()
    return name or user.username


def _roster_name(user, class_note):
    """
    Short name, with a trailing * for a student whose note records a nationality
    other than Irish. The note is the only nationality we hold, so a blank note
    reads as unmarked rather than as Irish.
    """
    name = _short_name(user)
    note = (class_note.note if class_note else '') or ''
    if note and not note.lower().startswith('irish'):
        name += '*'
    return name


# ------------------------------------------------------------
# Dashboard
# ------------------------------------------------------------

@teacher_required
def dashboard(request):
    teacher_profile = request.user.teacher_profile
    classes = (
        teacher_profile.classes.filter(is_active=True)
        .annotate(num_students=Count('students', distinct=True))
        .order_by('name')
    )
    today = timezone.localdate()

    # Today's timetabled slots, with a recorded/not chip each
    today_slots = (
        TimetableSlot.objects.filter(
            teacher_class__in=classes, weekday=today.weekday(), is_active=True
        )
        .select_related('teacher_class')
        .order_by('start_time')
    )
    recorded_slot_ids = set(
        ClassSession.objects.filter(
            teacher_class__in=classes, date=today, slot__isnull=False
        ).values_list('slot_id', flat=True)
    )
    recorded_slotless_class_ids = set(
        ClassSession.objects.filter(
            teacher_class__in=classes, date=today, slot__isnull=True
        ).values_list('teacher_class_id', flat=True)
    )
    todays_classes = [
        {
            'slot': slot,
            'teacher_class': slot.teacher_class,
            'recorded': slot.id in recorded_slot_ids
            or slot.teacher_class_id in recorded_slotless_class_ids,
        }
        for slot in today_slots
    ]

    # Recent gaps: timetabled slots in the last 7 days (excl. today) with no session
    gaps = []
    sessions_last_week = set(
        ClassSession.objects.filter(
            teacher_class__in=classes, date__gte=today - timedelta(days=7), date__lt=today
        ).values_list('teacher_class_id', 'date')
    )
    all_slots = TimetableSlot.objects.filter(
        teacher_class__in=classes, is_active=True
    ).select_related('teacher_class')
    for offset in range(7, 0, -1):
        day = today - timedelta(days=offset)
        for slot in all_slots:
            if slot.weekday == day.weekday() and (slot.teacher_class_id, day) not in sessions_last_week:
                gaps.append({'teacher_class': slot.teacher_class, 'date': day, 'slot': slot})

    context = {
        'classes': classes,
        'todays_classes': todays_classes,
        'gaps': gaps,
        'today': today,
    }
    return render(request, 'reports/dashboard.html', context)


# ------------------------------------------------------------
# Daily entry
# ------------------------------------------------------------

@teacher_required
def daily_entry(request, class_id):
    teacher_class = _get_owned_class(request, class_id)
    date = _parse_date(request.GET.get('date'), timezone.localdate())

    slot = None
    slot_id = request.GET.get('slot')
    if slot_id:
        slot = get_object_or_404(TimetableSlot, id=slot_id, teacher_class=teacher_class)
    else:
        day_slots = list(teacher_class.timetable_slots.filter(weekday=date.weekday(), is_active=True))
        if len(day_slots) == 1:
            slot = day_slots[0]

    session, _created = ClassSession.objects.get_or_create(
        teacher_class=teacher_class, date=date, slot=slot
    )

    roster = list(_roster(teacher_class))
    StudentSessionRecord.objects.bulk_create(
        [StudentSessionRecord(session=session, student=s) for s in roster],
        ignore_conflicts=True,
    )
    records = list(
        session.records.select_related('student', 'comment_preset').order_by(
            'student__first_name', 'student__last_name', 'student__username'
        )
    )

    # Activity badge: any NumScoil work since midnight of the previous session's date
    previous_session = (
        ClassSession.objects.filter(teacher_class=teacher_class, date__lt=date)
        .order_by('-date')
        .first()
    )
    since = _day_start(previous_session.date if previous_session else date - timedelta(days=7))
    active_ids = services.user_ids_active_since(roster, since)

    behaviour_presets = CommentPreset.objects.filter(category='behaviour', is_active=True)

    # Standing ability/note per student, in one query. Rows only exist for students
    # the teacher has actually rated, so a missing key is the unrated state.
    notes = {n.student_id: n for n in StudentClassNote.objects.filter(teacher_class=teacher_class)}
    for record in records:
        record.class_note = notes.get(record.student_id)
        record.roster_name = _roster_name(record.student, record.class_note)

    context = {
        'teacher_class': teacher_class,
        'session': session,
        'records': records,
        'active_ids': active_ids,
        'behaviour_presets': behaviour_presets,
        'date': date,
        'prev_date': date - timedelta(days=1),
        'next_date': date + timedelta(days=1),
        'today': timezone.localdate(),
        'since': since,
        'attendance_choices': StudentSessionRecord.ATTENDANCE_CHOICES,
        'homework_choices': StudentSessionRecord.HOMEWORK_CHOICES,
        'ability_choices': StudentClassNote.ABILITY_CHOICES,
    }
    return render(request, 'reports/daily_entry.html', context)


@teacher_required
def set_record(request, record_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    record = get_object_or_404(
        StudentSessionRecord.objects.select_related('session__teacher_class__teacher'),
        id=record_id,
    )
    if not request.user.is_superuser and record.session.teacher_class.teacher != request.user.teacher_profile:
        raise PermissionDenied

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    field = data.get('field')
    if field == 'attendance':
        value = data.get('value')
        if value not in dict(StudentSessionRecord.ATTENDANCE_CHOICES):
            return JsonResponse({'error': 'Invalid attendance value'}, status=400)
        record.attendance = value
        record.save(update_fields=['attendance', 'updated_at'])
        return JsonResponse({'ok': True, 'field': field, 'value': value})

    if field == 'homework':
        value = data.get('value')
        if value not in dict(StudentSessionRecord.HOMEWORK_CHOICES):
            return JsonResponse({'error': 'Invalid homework value'}, status=400)
        record.homework = value
        record.save(update_fields=['homework', 'updated_at'])
        return JsonResponse({'ok': True, 'field': field, 'value': value})

    if field == 'comment':
        preset_id = data.get('preset_id')
        preset = None
        if preset_id:
            try:
                preset = CommentPreset.objects.get(id=preset_id, category='behaviour')
            except CommentPreset.DoesNotExist:
                return JsonResponse({'error': 'Unknown preset'}, status=400)
        record.comment_preset = preset
        record.comment_text = (data.get('text') or '')[:300]
        record.save(update_fields=['comment_preset', 'comment_text', 'updated_at'])
        return JsonResponse({
            'ok': True,
            'field': field,
            'has_comment': record.has_comment,
        })

    return JsonResponse({'error': 'Unknown field'}, status=400)


@teacher_required
def set_homework_due(request, session_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    session = get_object_or_404(
        ClassSession.objects.select_related('teacher_class__teacher'), id=session_id
    )
    if not request.user.is_superuser and session.teacher_class.teacher != request.user.teacher_profile:
        raise PermissionDenied
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    session.homework_due = bool(data.get('homework_due'))
    session.save(update_fields=['homework_due', 'updated_at'])
    return JsonResponse({'ok': True, 'homework_due': session.homework_due})


@teacher_required
def set_student_note(request, class_id, student_id):
    """Standing ability/note for one student in one class. Row is created on first use."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    teacher_class = _get_owned_class(request, class_id)
    student = get_object_or_404(teacher_class.students, id=student_id)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    field = data.get('field')
    if field not in ('ability', 'note'):
        return JsonResponse({'error': 'Unknown field'}, status=400)

    value = data.get('value') or ''
    if field == 'ability' and value and value not in dict(StudentClassNote.ABILITY_CHOICES):
        return JsonResponse({'error': 'Invalid ability value'}, status=400)
    if field == 'note':
        value = value[:300]

    note, _created = StudentClassNote.objects.get_or_create(
        teacher_class=teacher_class, student=student
    )
    setattr(note, field, value)
    note.save(update_fields=[field, 'updated_at'])

    return JsonResponse({
        'ok': True,
        'field': field,
        'value': value,
        'updated_at': note.updated_at.strftime('%-d %b'),
    })


# ------------------------------------------------------------
# Class overview
# ------------------------------------------------------------

def _overview_data(teacher_class, num_sessions):
    sessions = list(
        ClassSession.objects.filter(teacher_class=teacher_class)
        .select_related('slot')
        .order_by('-date', 'slot__start_time')[:num_sessions]
    )
    sessions.reverse()  # oldest → newest across the grid
    records = StudentSessionRecord.objects.filter(session__in=sessions).select_related(
        'session', 'comment_preset'
    )
    by_student = {}
    for record in records:
        by_student.setdefault(record.student_id, {})[record.session_id] = record

    rows = []
    for student in _roster(teacher_class):
        student_records = by_student.get(student.id, {})
        cells = [student_records.get(s.id) for s in sessions]
        recorded = [r for r in cells if r is not None]
        attended = [r for r in recorded if r.attendance in ('present', 'late')]
        late = [r for r in recorded if r.attendance == 'late']
        hw_recorded = [r for r in recorded if r.session.homework_due]
        hw_done = [r for r in hw_recorded if r.homework == 'done']
        rows.append({
            'student': student,
            'cells': cells,
            'attendance_pct': round(len(attended) / len(recorded) * 100) if recorded else None,
            'late_count': len(late),
            'homework_pct': round(len(hw_done) / len(hw_recorded) * 100) if hw_recorded else None,
        })
    return sessions, rows


@teacher_required
def class_overview(request, class_id):
    teacher_class = _get_owned_class(request, class_id)
    try:
        num_sessions = min(max(int(request.GET.get('sessions', 10)), 1), 50)
    except ValueError:
        num_sessions = 10
    sessions, rows = _overview_data(teacher_class, num_sessions)

    expected = None
    if sessions and teacher_class.timetable_slots.filter(is_active=True).exists():
        slots = list(teacher_class.timetable_slots.filter(is_active=True))
        first, last = sessions[0].date, sessions[-1].date
        expected = 0
        day = first
        while day <= last:
            expected += sum(1 for s in slots if s.weekday == day.weekday())
            day += timedelta(days=1)

    context = {
        'teacher_class': teacher_class,
        'sessions': sessions,
        'rows': rows,
        'num_sessions': num_sessions,
        'expected_sessions': expected,
    }
    return render(request, 'reports/class_overview.html', context)


@teacher_required
def class_overview_csv(request, class_id):
    teacher_class = _get_owned_class(request, class_id)
    sessions, rows = _overview_data(teacher_class, 50)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = (
        f'attachment; filename="{teacher_class.name}-overview.csv"'
    )
    writer = csv.writer(response)
    writer.writerow(
        ['Student', 'Attendance %', 'Late count', 'Homework %']
        + [s.date.isoformat() for s in sessions]
    )
    for row in rows:
        cells = []
        for record in row['cells']:
            if record is None:
                cells.append('')
            else:
                cell = f"{record.get_attendance_display()} / HW {record.get_homework_display()}"
                if record.has_comment:
                    comment = record.comment_preset.text if record.comment_preset else ''
                    cell += f" / {comment} {record.comment_text}".rstrip()
                cells.append(cell)
        writer.writerow([
            row['student'].get_full_name() or row['student'].username,
            row['attendance_pct'] if row['attendance_pct'] is not None else '',
            row['late_count'],
            row['homework_pct'] if row['homework_pct'] is not None else '',
        ] + cells)
    return response


# ------------------------------------------------------------
# Class tests
# ------------------------------------------------------------

@teacher_required
def test_list(request, class_id):
    teacher_class = _get_owned_class(request, class_id)

    if request.method == 'POST':
        name = (request.POST.get('name') or '').strip()
        date = _parse_date(request.POST.get('date'), timezone.localdate())
        try:
            max_marks = int(request.POST.get('max_marks', 100))
        except ValueError:
            max_marks = 100
        if not name:
            messages.error(request, 'Please give the test a name.')
        elif max_marks < 1:
            messages.error(request, 'Max marks must be at least 1.')
        else:
            test = ClassTest.objects.create(
                teacher_class=teacher_class, name=name, date=date, max_marks=max_marks
            )
            messages.success(request, f'Test "{test.name}" created — enter results below.')
            return redirect('reports:test_detail', test_id=test.id)

    tests = teacher_class.tests.annotate(
        avg_score=Avg('results__score'), num_results=Count('results')
    )
    context = {
        'teacher_class': teacher_class,
        'tests': tests,
        'today': timezone.localdate(),
    }
    return render(request, 'reports/test_list.html', context)


@teacher_required
def test_detail(request, test_id):
    test = get_object_or_404(
        ClassTest.objects.select_related('teacher_class__teacher'), id=test_id
    )
    if not request.user.is_superuser and test.teacher_class.teacher != request.user.teacher_profile:
        raise PermissionDenied

    roster = list(_roster(test.teacher_class))

    if request.method == 'POST':
        errors = []
        for student in roster:
            raw_score = (request.POST.get(f'score_{student.id}') or '').strip()
            score = None
            if raw_score:
                try:
                    score = Decimal(raw_score)
                except InvalidOperation:
                    errors.append(f'Invalid score for {student.get_full_name() or student.username}.')
                    continue
                if score < 0 or score > test.max_marks:
                    errors.append(
                        f'Score for {student.get_full_name() or student.username} must be between 0 and {test.max_marks}.'
                    )
                    continue
            preset_id = request.POST.get(f'preset_{student.id}') or None
            preset = None
            if preset_id:
                preset = CommentPreset.objects.filter(id=preset_id, category='test').first()
            TestResult.objects.update_or_create(
                test=test,
                student=student,
                defaults={
                    'score': score,
                    'comment_preset': preset,
                    'comment_text': (request.POST.get(f'comment_{student.id}') or '').strip()[:300],
                },
            )
        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            messages.success(request, 'Results saved.')
        return redirect('reports:test_detail', test_id=test.id)

    results = {r.student_id: r for r in test.results.select_related('comment_preset')}
    rows = [{'student': s, 'result': results.get(s.id)} for s in roster]

    scores = [float(r.score) for r in results.values() if r.score is not None]
    stats = None
    if scores:
        stats = {
            'avg': round(sum(scores) / len(scores), 1),
            'high': max(scores),
            'low': min(scores),
            'sat': len(scores),
        }

    context = {
        'test': test,
        'rows': rows,
        'stats': stats,
        'test_presets': CommentPreset.objects.filter(category='test', is_active=True),
    }
    return render(request, 'reports/test_detail.html', context)


@teacher_required
def test_delete(request, test_id):
    if request.method != 'POST':
        return redirect('reports:dashboard')
    test = get_object_or_404(
        ClassTest.objects.select_related('teacher_class__teacher'), id=test_id
    )
    if not request.user.is_superuser and test.teacher_class.teacher != request.user.teacher_profile:
        raise PermissionDenied
    class_id = test.teacher_class_id
    name = test.name
    test.delete()
    messages.success(request, f'Test "{name}" deleted.')
    return redirect('reports:test_list', class_id=class_id)


# ------------------------------------------------------------
# Student report
# ------------------------------------------------------------

ACTIVITY_LEVELS = [(0, 0), (2, 1), (5, 2), (10, 3)]  # (upper bound, level); above → 4

ACTIVITY_LABELS = {
    'questions': 'Practice questions',
    'homework_tasks': 'Homework tasks completed',
    'flashcards': 'Flashcards',
    'quickkicks': 'QuickKicks',
    'exams': 'Exam attempts',
}


def _activity_level(total):
    for bound, level in ACTIVITY_LEVELS:
        if total <= bound:
            return level
    return 4


def _student_report_data(request, student, start, end):
    """Everything the student report needs; shared by HTML, CSV and PDF views."""
    teacher_profile = request.user.teacher_profile if not request.user.is_superuser else None
    if teacher_profile:
        class_filter = {'teacher_class__teacher': teacher_profile}
    else:
        class_filter = {}

    records = list(
        StudentSessionRecord.objects.filter(
            student=student,
            session__date__gte=start,
            session__date__lte=end,
            **{f'session__{k}': v for k, v in class_filter.items()},
        ).select_related('session', 'comment_preset')
    )
    recorded = len(records)
    attendance = {
        'recorded': recorded,
        'present': sum(1 for r in records if r.attendance == 'present'),
        'late': sum(1 for r in records if r.attendance == 'late'),
        'absent': sum(1 for r in records if r.attendance == 'absent'),
    }
    attendance['pct'] = (
        round((attendance['present'] + attendance['late']) / recorded * 100) if recorded else None
    )
    hw_records = [r for r in records if r.session.homework_due]
    homework = {
        'recorded': len(hw_records),
        'done': sum(1 for r in hw_records if r.homework == 'done'),
        'partial': sum(1 for r in hw_records if r.homework == 'partial'),
        'not_done': sum(1 for r in hw_records if r.homework == 'not_done'),
    }
    homework['pct'] = round(homework['done'] / len(hw_records) * 100) if hw_records else None

    test_results = list(
        TestResult.objects.filter(
            student=student,
            test__date__gte=start,
            test__date__lte=end,
            **{f'test__{k}': v for k, v in class_filter.items()},
        ).select_related('test', 'comment_preset').order_by('test__date')
    )

    # Merged comment trail (session behaviour comments + test comments)
    comments = []
    for r in records:
        if r.has_comment:
            comments.append({
                'date': r.session.date,
                'kind': 'behaviour',
                'preset': r.comment_preset,
                'text': r.comment_text,
                'context': r.session.teacher_class.name,
            })
    for r in test_results:
        if r.has_comment:
            comments.append({
                'date': r.test.date,
                'kind': 'test',
                'preset': r.comment_preset,
                'text': r.comment_text,
                'context': r.test.name,
            })
    comments.sort(key=lambda c: c['date'], reverse=True)

    # Automatic NumScoil activity
    start_dt = _day_start(start)
    end_dt = _day_start(end + timedelta(days=1))
    activity = services.get_activity_by_day([student], start_dt, end_dt)
    totals = services.activity_totals(activity, student.id)
    per_day = activity.get(student.id, {})
    strip = []
    day = start
    while day <= end:
        total = per_day.get(day, {}).get('total', 0)
        strip.append({'date': day, 'total': total, 'level': _activity_level(total)})
        day += timedelta(days=1)
    active_days = sum(1 for s in strip if s['total'])

    return {
        'student': student,
        'start': start,
        'end': end,
        'attendance': attendance,
        'homework': homework,
        'test_results': test_results,
        'comments': comments,
        'activity_totals': totals,
        'activity_labels': ACTIVITY_LABELS,
        'strip': strip,
        'active_days': active_days,
    }


@teacher_required
def student_report(request, student_id):
    student = _get_owned_student(request, student_id)
    end = _parse_date(request.GET.get('end'), timezone.localdate())
    start = _parse_date(request.GET.get('start'), end - timedelta(days=29))
    if start > end:
        start, end = end, start
    context = _student_report_data(request, student, start, end)
    return render(request, 'reports/student_report.html', context)


@teacher_required
def student_report_csv(request, student_id):
    student = _get_owned_student(request, student_id)
    end = _parse_date(request.GET.get('end'), timezone.localdate())
    start = _parse_date(request.GET.get('start'), end - timedelta(days=29))
    data = _student_report_data(request, student, start, end)

    response = HttpResponse(content_type='text/csv')
    name = student.get_full_name() or student.username
    response['Content-Disposition'] = f'attachment; filename="{name}-report-{start}-{end}.csv"'
    writer = csv.writer(response)
    writer.writerow(['Student report', name, f'{start} to {end}'])
    writer.writerow([])
    writer.writerow(['Attendance %', data['attendance']['pct'], 'Present', data['attendance']['present'],
                     'Late', data['attendance']['late'], 'Absent', data['attendance']['absent']])
    writer.writerow(['Homework done %', data['homework']['pct'], 'Done', data['homework']['done'],
                     'Partial', data['homework']['partial'], 'Not done', data['homework']['not_done']])
    writer.writerow([])
    writer.writerow(['NumScoil activity'])
    for key, label in ACTIVITY_LABELS.items():
        writer.writerow([label, data['activity_totals'].get(key, 0)])
    writer.writerow(['Active days', data['active_days']])
    writer.writerow([])
    writer.writerow(['Tests'])
    writer.writerow(['Date', 'Test', 'Score', 'Out of', '%', 'Comment'])
    for r in data['test_results']:
        comment = ' '.join(filter(None, [r.comment_preset.text if r.comment_preset else '', r.comment_text]))
        writer.writerow([r.test.date, r.test.name, r.score if r.score is not None else 'Absent',
                         r.test.max_marks, r.percentage if r.percentage is not None else '', comment])
    writer.writerow([])
    writer.writerow(['Comments'])
    writer.writerow(['Date', 'Type', 'Context', 'Comment'])
    for c in data['comments']:
        comment = ' '.join(filter(None, [c['preset'].text if c['preset'] else '', c['text']]))
        writer.writerow([c['date'], c['kind'], c['context'], comment])
    return response


@teacher_required
def student_report_pdf(request, student_id):
    student = _get_owned_student(request, student_id)
    end = _parse_date(request.GET.get('end'), timezone.localdate())
    start = _parse_date(request.GET.get('start'), end - timedelta(days=29))
    data = _student_report_data(request, student, start, end)
    name = student.get_full_name() or student.username

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5 * inch, bottomMargin=0.5 * inch)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('ReportTitle', parent=styles['Heading1'], fontSize=16,
                                 textColor=colors.HexColor(MIDNIGHT_HEX))
    heading_style = ParagraphStyle('ReportHeading', parent=styles['Heading2'], fontSize=12,
                                   textColor=colors.HexColor(MIDNIGHT_HEX))
    elements = [
        Paragraph(f'Student Report — {name}', title_style),
        Paragraph(f'{start} to {end}', styles['Normal']),
        Spacer(1, 12),
    ]

    def _fmt_pct(value):
        return f'{value}%' if value is not None else '—'

    summary = Table([
        ['Attendance', _fmt_pct(data['attendance']['pct']),
         f"Present {data['attendance']['present']} · Late {data['attendance']['late']} · Absent {data['attendance']['absent']}"],
        ['Homework done', _fmt_pct(data['homework']['pct']),
         f"Done {data['homework']['done']} · Partial {data['homework']['partial']} · Not done {data['homework']['not_done']}"],
        ['NumScoil active days', str(data['active_days']),
         ' · '.join(f"{label} {data['activity_totals'].get(key, 0)}"
                    for key, label in ACTIVITY_LABELS.items() if data['activity_totals'].get(key))
         or 'No recorded activity'],
    ], colWidths=[1.6 * inch, 1.0 * inch, 3.9 * inch])
    summary.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E8EEF5')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements += [summary, Spacer(1, 16)]

    if data['test_results']:
        elements.append(Paragraph('Tests', heading_style))
        test_rows = [['Date', 'Test', 'Score', '%', 'Comment']]
        for r in data['test_results']:
            comment = ' '.join(filter(None, [r.comment_preset.text if r.comment_preset else '', r.comment_text]))
            test_rows.append([
                str(r.test.date), r.test.name,
                f'{r.score}/{r.test.max_marks}' if r.score is not None else 'Absent',
                f'{r.percentage}%' if r.percentage is not None else '—',
                Paragraph(comment, styles['Normal']),
            ])
        test_table = Table(test_rows, colWidths=[0.9 * inch, 1.8 * inch, 0.9 * inch, 0.6 * inch, 2.3 * inch])
        test_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(MIDNIGHT_HEX)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements += [test_table, Spacer(1, 16)]

    if data['comments']:
        elements.append(Paragraph('Comments', heading_style))
        comment_rows = [['Date', 'Context', 'Comment']]
        for c in data['comments']:
            comment = ' '.join(filter(None, [c['preset'].text if c['preset'] else '', c['text']]))
            comment_rows.append([str(c['date']), c['context'], Paragraph(comment, styles['Normal'])])
        comment_table = Table(comment_rows, colWidths=[0.9 * inch, 1.8 * inch, 3.8 * inch])
        comment_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(MIDNIGHT_HEX)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(comment_table)

    doc.build(elements)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{name}-report-{start}-{end}.pdf"'
    return response


# ------------------------------------------------------------
# PWA manifest
# ------------------------------------------------------------

@login_required
def manifest(request):
    return JsonResponse(
        {
            'name': 'NumScoil Reports',
            'short_name': 'Reports',
            'start_url': '/reports/',
            'scope': '/reports/',
            'display': 'standalone',
            'background_color': MIDNIGHT_HEX,
            'theme_color': MIDNIGHT_HEX,
            'icons': [
                {'src': '/static/images/numscoil_icon_192.png', 'sizes': '192x192', 'type': 'image/png'},
                {'src': '/static/images/numscoil_icon_512.png', 'sizes': '512x512', 'type': 'image/png'},
            ],
        },
        content_type='application/manifest+json',
    )
