"""Marking a teacher's exam: scanned scripts in, marks per part out.

Same access as the builder (exam_builder.py): @teacher_required, then every
exam through its owner and every script through its exam. A student can only
be chosen from the teacher's own classes. Script pages are private student
work, served by ``script_page`` alone.

The results are the teacher's: nothing here is shown to students. The marker
proposes a mark per part; the teacher's mark, where they give one, wins.
"""
import csv
import logging

from django.contrib import messages
from django.db import transaction
from django.http import FileResponse, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from students.decorators import teacher_required
from students.services.image_intake import ImageIntakeError, process_pdf_pages

from .models import ExamScript, ExamScriptMark, ExamScriptPage, ExamScriptQuestion, TeacherExam
from .services import script_marking
from .services.exam_pdf import exam_layout

logger = logging.getLogger(__name__)

MAX_SCRIPT_PAGES = 40
MAX_SCRIPT_BYTES = 40 * 1024 * 1024


def _own_exam(request, pk):
    return get_object_or_404(TeacherExam, pk=pk, owner=request.user)


def _own_script(request, pk, script_pk):
    exam = _own_exam(request, pk)
    return exam, get_object_or_404(ExamScript.objects.select_related('student'),
                                   pk=script_pk, exam=exam)


def _my_students(request):
    """Students in the teacher's active classes, with the class they are in."""
    profile = getattr(request.user, 'teacher_profile', None)
    if profile is None:
        return []
    seen, out = set(), []
    for teacher_class in profile.classes.filter(is_active=True).prefetch_related('students').order_by('name'):
        for student in teacher_class.students.order_by('last_name', 'first_name', 'username'):
            if student.pk not in seen:
                seen.add(student.pk)
                out.append((teacher_class, student))
    return out


def student_name(user):
    return user.get_full_name() or user.username


@teacher_required
def marking_overview(request, pk):
    exam = _own_exam(request, pk)
    items = list(exam.ordered_items())
    scripts = list(exam.scripts.select_related('student').prefetch_related(
        'questions__marks', 'questions__item'))
    rows = []
    for script in scripts:
        by_item = {q.item_id: q for q in script.questions.all()}
        cells = [by_item.get(item.id) for item in items]
        awarded, possible = script.total
        rows.append({
            'script': script,
            'cells': [(q, q.total if q else (None, item.marks)) for q, item in zip(cells, items)],
            'awarded': awarded, 'possible': possible,
            'pending': sum(1 for q in cells if q and q.status == ExamScriptQuestion.PENDING),
        })
    taken = {script.student_id for script in scripts}
    return render(request, 'exam_papers/exam_marking.html', {
        'exam': exam, 'items': items, 'rows': rows,
        'total_marks': sum(item.marks for item in items),
        'student_groups': _grouped([(c, s) for c, s in _my_students(request) if s.pk not in taken]),
    })


def _grouped(pairs):
    """[(class, [students])] in order, for the picker's optgroups."""
    groups = []
    for teacher_class, student in pairs:
        if not groups or groups[-1][0] != teacher_class:
            groups.append((teacher_class, []))
        groups[-1][1].append(student)
    return groups


@teacher_required
@require_POST
def script_upload(request, pk):
    exam = _own_exam(request, pk)
    students = {s.pk: s for _, s in _my_students(request)}
    student = students.get(int(request.POST.get('student') or 0))
    upload = request.FILES.get('scan')
    if student is None:
        messages.error(request, 'Choose a student from one of your classes.')
        return redirect('exam_papers:marking_overview', exam.pk)
    if upload is None:
        messages.error(request, 'Choose the scanned PDF of their script.')
        return redirect('exam_papers:marking_overview', exam.pk)
    if upload.size > MAX_SCRIPT_BYTES:
        messages.error(request, 'That file is over 40 MB. Scan at a lower resolution, or in greyscale.')
        return redirect('exam_papers:marking_overview', exam.pk)
    if ExamScript.objects.filter(exam=exam, student=student).exists():
        messages.error(request, f'{student_name(student)} already has a script on this exam. '
                                'Delete it first to upload a new scan.')
        return redirect('exam_papers:marking_overview', exam.pk)
    if not exam.items.exists():
        messages.error(request, 'This exam has no questions.')
        return redirect('exam_papers:marking_overview', exam.pk)

    try:
        pages = process_pdf_pages(upload.read(), max_pages=MAX_SCRIPT_PAGES)
    except ImageIntakeError as e:
        messages.error(request, str(e))
        return redirect('exam_papers:marking_overview', exam.pk)

    layout = exam_layout(exam)
    expected = max(last for _, last in layout.values())
    lines_up = len(pages) == expected
    with transaction.atomic():
        script = ExamScript.objects.create(exam=exam, student=student, page_count=len(pages),
                                           expected_pages=expected)
        for number, (content, _w, _h, _size) in enumerate(pages, start=1):
            row = ExamScriptPage(script=script, number=number)
            row.image.save(f'{number}.jpg', content, save=False)
            row.save()
        for item in exam.ordered_items():
            first, last = layout.get(item.id, (None, None))
            question = ExamScriptQuestion.objects.create(
                script=script, item=item,
                first_page=first if lines_up else None, last_page=last if lines_up else None)
            script_marking.ensure_mark_rows(question)
    if lines_up:
        messages.success(request, f'{student_name(student)}: {len(pages)} pages, lined up with the exam. '
                                  'Press "Mark this script".')
    else:
        messages.error(request, f'{student_name(student)}: the scan has {len(pages)} pages but the exam '
                                f'has {expected}, so the pages can\'t be matched automatically. '
                                'Set each question\'s pages below, then mark it.')
    return redirect('exam_papers:script_detail', exam.pk, script.pk)


@teacher_required
def script_detail(request, pk, script_pk):
    exam, script = _own_script(request, pk, script_pk)
    questions = list(script.ordered_questions())
    numbered = [(n, q) for n, q in enumerate(questions, start=1)]
    awarded, possible = script.total
    return render(request, 'exam_papers/exam_script.html', {
        'exam': exam, 'script': script, 'questions': numbered,
        'awarded': awarded, 'possible': possible,
        'pages': list(script.pages.values_list('number', flat=True)),
        'pending': sum(1 for q in questions if q.status == ExamScriptQuestion.PENDING),
        'student_name': student_name(script.student),
    })


@teacher_required
def script_page(request, pk, script_pk, number):
    _, script = _own_script(request, pk, script_pk)
    page = get_object_or_404(ExamScriptPage, script=script, number=number)
    response = FileResponse(page.image.open('rb'), content_type='image/jpeg')
    response['Cache-Control'] = 'private, no-store'
    return response


@teacher_required
@require_POST
def script_mark_next(request, pk, script_pk):
    """Mark one pending question. The page calls this until 'complete'."""
    _, script = _own_script(request, pk, script_pk)
    question = script_marking.next_pending(script)
    if question is not None:
        try:
            script_marking.mark_question(question)
        except script_marking.Stalled as e:
            return JsonResponse({'success': False, 'message': str(e)})
        except Exception:
            logger.exception('Exam script %s question %s failed', script.pk, question.pk)
            question.status = ExamScriptQuestion.FAILED
            question.message = script_marking.FAILED_MESSAGE
            question.save(update_fields=['status', 'message'])
    total = script.questions.count()
    pending = script.questions.filter(status=ExamScriptQuestion.PENDING).count()
    return JsonResponse({'success': True, 'done': total - pending, 'total': total,
                         'complete': pending == 0})


def _int_or_none(raw, low, high):
    raw = (raw or '').strip()
    if raw == '':
        return None
    try:
        value = int(raw)
    except ValueError:
        raise ValueError(raw)
    if not low <= value <= high:
        raise ValueError(raw)
    return value


@teacher_required
@require_POST
def script_save(request, pk, script_pk):
    """The teacher's marks, feedback, page ranges and comment for a script."""
    exam, script = _own_script(request, pk, script_pk)
    problems = []
    with transaction.atomic():
        for question in script.questions.all():
            if f'first_{question.pk}' not in request.POST and f'last_{question.pk}' not in request.POST:
                continue
            try:
                first = _int_or_none(request.POST.get(f'first_{question.pk}'), 1, script.page_count)
                last = _int_or_none(request.POST.get(f'last_{question.pk}'), 1, script.page_count)
            except ValueError:
                problems.append('Page numbers must be pages of this scan.')
                continue
            if first and last and first > last:
                first, last = last, first
            if (first, last) != (question.first_page, question.last_page):
                # New pages mean the old reading is of the wrong page: mark again.
                question.first_page, question.last_page = first, last
                question.status = ExamScriptQuestion.PENDING
                question.message = ''
                question.save()
                question.marks.update(ai_mark=None, transcription='', reasoning='')
        for mark in ExamScriptMark.objects.filter(question__script=script):
            if f'mark_{mark.pk}' not in request.POST:
                continue
            try:
                mark.teacher_mark = _int_or_none(request.POST.get(f'mark_{mark.pk}'), 0, mark.max_marks)
            except ValueError:
                problems.append(f'{mark.label}: a mark must be a whole number from 0 to {mark.max_marks}.')
                continue
            if f'feedback_{mark.pk}' in request.POST:
                mark.feedback = request.POST.get(f'feedback_{mark.pk}', '')[:2000]
            mark.save(update_fields=['teacher_mark', 'feedback'])
        script.teacher_comment = request.POST.get('teacher_comment', script.teacher_comment)[:2000]
        script.reviewed_at = timezone.now() if request.POST.get('reviewed') == '1' else None
        script.save(update_fields=['teacher_comment', 'reviewed_at', 'updated_at'])
    for problem in dict.fromkeys(problems):
        messages.error(request, problem)
    if not problems:
        messages.success(request, 'Saved.')
    return redirect('exam_papers:script_detail', exam.pk, script.pk)


@teacher_required
@require_POST
def script_remark(request, pk, script_pk, question_pk):
    """Send one question back to the marker. The teacher's own marks stay."""
    exam, script = _own_script(request, pk, script_pk)
    question = get_object_or_404(ExamScriptQuestion, pk=question_pk, script=script)
    question.status = ExamScriptQuestion.PENDING
    question.message = ''
    question.save(update_fields=['status', 'message'])
    return redirect('exam_papers:script_detail', exam.pk, script.pk)


@teacher_required
@require_POST
def script_delete(request, pk, script_pk):
    exam, script = _own_script(request, pk, script_pk)
    name = student_name(script.student)
    for page in script.pages.all():
        page.image.delete(save=False)
    script.delete()
    messages.success(request, f"Deleted {name}'s script.")
    return redirect('exam_papers:marking_overview', exam.pk)


@teacher_required
def results_sheet(request, pk, script_pk):
    exam, script = _own_script(request, pk, script_pk)
    awarded, possible = script.total
    return render(request, 'exam_papers/exam_results_print.html', {
        'exam': exam, 'script': script, 'student_name': student_name(script.student),
        'questions': list(enumerate(script.ordered_questions(), start=1)),
        'awarded': awarded, 'possible': possible,
    })


@teacher_required
def results_csv(request, pk):
    exam = _own_exam(request, pk)
    items = list(exam.ordered_items())
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{slugify(exam.title) or "exam"}-results.csv"'
    writer = csv.writer(response)
    writer.writerow(['Student', 'Username']
                    + [f'Q{n} (/{item.marks})' for n, item in enumerate(items, start=1)]
                    + [f'Total (/{sum(i.marks for i in items)})', 'Reviewed'])
    for script in exam.scripts.select_related('student').prefetch_related('questions__marks'):
        by_item = {q.item_id: q for q in script.questions.all()}
        cells = []
        for item in items:
            question = by_item.get(item.id)
            got = question.total[0] if question else None
            cells.append('' if got is None else got)
        awarded, _ = script.total
        writer.writerow([student_name(script.student), script.student.username] + cells
                        + ['' if awarded is None else awarded, 'yes' if script.reviewed_at else 'no'])
    return response
