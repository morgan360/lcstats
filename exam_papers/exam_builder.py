"""Teachers put together their own exam from past exam questions, and print it.

Access is the Homework Check pattern: @teacher_required for the group, then
every exam fetched through its owner, so one teacher can neither see nor change
another's - a guessed id is a 404, not someone else's exam.

Adding, removing and reordering are plain form posts that come back to the
builder, to the topic and the card the teacher was on.
"""
from django.contrib import messages
from django.db import transaction
from django.db.models import Max, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from core.models import Subject
from interactive_lessons.models import Topic
from students.decorators import teacher_required

from .forms import TeacherExamForm
from .models import ExamQuestion, TeacherExam, TeacherExamQuestion, question_marks
from .services.topic_questions import topic_filter


def _own_exam(request, pk):
    return get_object_or_404(TeacherExam, pk=pk, owner=request.user)


def _questions_with_images():
    return ExamQuestion.objects.exclude(image='').exclude(image__isnull=True)


def _back(exam, topic_id=None, anchor=None):
    url = reverse('exam_papers:exam_builder', args=[exam.pk])
    if topic_id:
        url += f'?topic={topic_id}'
    if anchor:
        url += f'#{anchor}'
    return redirect(url)


@teacher_required
def my_exams(request):
    exams = TeacherExam.objects.filter(owner=request.user).prefetch_related(
        'items__question__parts')
    return render(request, 'exam_papers/my_exams.html', {'exams': exams})


@teacher_required
@require_POST
def exam_create(request):
    subject = (getattr(request, 'current_subject', None)
               or Subject.objects.filter(slug='maths').first())
    title = (request.POST.get('title') or '').strip()[:120] or 'New exam'
    exam = TeacherExam.objects.create(owner=request.user, subject=subject, title=title)
    return redirect('exam_papers:exam_builder', exam.pk)


@teacher_required
def exam_builder(request, pk):
    exam = _own_exam(request, pk)
    items = list(exam.ordered_items())
    chosen_ids = {item.question_id for item in items}

    with_images = _questions_with_images().filter(exam_paper__subject=exam.subject)
    topics = Topic.objects.filter(subject=exam.subject).filter(
        Q(exam_questions__in=with_images)
        | Q(secondary_exam_questions__in=with_images.filter(list_under_secondary=True))
    ).distinct().order_by('order', 'name')

    selected_topic = request.GET.get('topic', '')
    candidates = []
    if selected_topic.isdigit():
        candidates = list(with_images.filter(topic_filter(int(selected_topic))).distinct().select_related(
            'exam_paper', 'topic').prefetch_related('parts').order_by(
            '-exam_paper__year', 'exam_paper__paper_type', 'question_number'))
    # Each card shows its marks, and whether (and where) it is in the exam already.
    position = {item.question_id: (n, item) for n, item in enumerate(items, start=1)}
    for question in candidates:
        question.marks = question_marks(question)
        question.exam_position, question.exam_item = position.get(question.id, (None, None))

    return render(request, 'exam_papers/exam_builder.html', {
        'exam': exam,
        'form': TeacherExamForm(instance=exam),
        'items': items,
        'total_marks': sum(item.marks for item in items),
        'topics': topics,
        'selected_topic': selected_topic,
        'candidates': candidates,
        'chosen_ids': chosen_ids,
    })


@teacher_required
@require_POST
def exam_save_details(request, pk):
    exam = _own_exam(request, pk)
    form = TeacherExamForm(request.POST, instance=exam)
    if form.is_valid():
        form.save()
        messages.success(request, 'Exam details saved.')
    else:
        messages.error(request, 'Those details could not be saved: '
                       + '; '.join(f'{field}: {", ".join(errs)}' for field, errs in form.errors.items()))
    return _back(exam, request.POST.get('topic'))


@teacher_required
@require_POST
def exam_add_question(request, pk):
    exam = _own_exam(request, pk)
    question = get_object_or_404(_questions_with_images(), pk=request.POST.get('question_id'),
                                 exam_paper__subject=exam.subject)
    with transaction.atomic():
        top = exam.items.aggregate(top=Max('order'))['top']
        TeacherExamQuestion.objects.get_or_create(
            exam=exam, question=question,
            defaults={'order': 0 if top is None else top + 1})
        exam.save(update_fields=['updated_at'])
    return _back(exam, request.POST.get('topic'), f'q-{question.pk}')


@teacher_required
@require_POST
def exam_remove_question(request, pk, item_pk):
    exam = _own_exam(request, pk)
    item = get_object_or_404(TeacherExamQuestion, pk=item_pk, exam=exam)
    question_id = item.question_id
    with transaction.atomic():
        item.delete()
        _renumber(exam)
    anchor = f'q-{question_id}' if request.POST.get('from') == 'picker' else 'exam-questions'
    return _back(exam, request.POST.get('topic'), anchor)


@teacher_required
@require_POST
def exam_move_question(request, pk, item_pk):
    exam = _own_exam(request, pk)
    get_object_or_404(TeacherExamQuestion, pk=item_pk, exam=exam)
    step = -1 if request.POST.get('direction') == 'up' else 1
    with transaction.atomic():
        items = list(exam.items.select_for_update().order_by('order', 'id'))
        index = next(i for i, item in enumerate(items) if item.pk == int(item_pk))
        other = index + step
        if 0 <= other < len(items):
            items[index], items[other] = items[other], items[index]
            _renumber(exam, items)
    return _back(exam, request.POST.get('topic'), 'exam-questions')


@teacher_required
@require_POST
def exam_set_omitted(request, pk, item_pk):
    """Which parts of one question students are told not to answer."""
    exam = _own_exam(request, pk)
    item = get_object_or_404(TeacherExamQuestion, pk=item_pk, exam=exam)
    wanted = {int(v) for v in request.POST.getlist('omit') if v.isdigit()}
    # Only this question's own parts, and never all of them: a question with
    # nothing left to answer belongs out of the exam, not in it at 0 marks.
    parts = [part for part in item.question.parts.all() if part.id in wanted]
    if parts and len(parts) == item.question.parts.count():
        messages.error(request, 'That would leave nothing to answer. Remove the question instead.')
        return _back(exam, request.POST.get('topic'), 'exam-questions')
    item.omitted_parts.set(parts)
    exam.save(update_fields=['updated_at'])
    return _back(exam, request.POST.get('topic'), 'exam-questions')


def _renumber(exam, items=None):
    """Orders 0, 1, 2 ... in the given (or current) order, with no gaps."""
    items = items if items is not None else list(exam.items.order_by('order', 'id'))
    for order, item in enumerate(items):
        if item.order != order:
            item.order = order
            item.save(update_fields=['order'])
    exam.save(update_fields=['updated_at'])


@teacher_required
@require_POST
def exam_delete(request, pk):
    exam = _own_exam(request, pk)
    title = exam.title
    exam.delete()
    messages.success(request, f'Deleted "{title}".')
    return redirect('exam_papers:my_exams')


def _pdf_response(data, name):
    response = HttpResponse(data, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{slugify(name) or "exam"}.pdf"'
    return response


@teacher_required
def exam_pdf(request, pk):
    from .services.exam_pdf import build_exam_pdf
    exam = _own_exam(request, pk)
    if not exam.items.exists():
        messages.error(request, 'Add at least one question first.')
        return _back(exam)
    return _pdf_response(build_exam_pdf(exam), exam.title)


@teacher_required
def exam_scheme_pdf(request, pk):
    from .services.exam_pdf import build_exam_scheme_pdf
    exam = _own_exam(request, pk)
    if not exam.items.exists():
        messages.error(request, 'Add at least one question first.')
        return _back(exam)
    return _pdf_response(build_exam_scheme_pdf(exam), f'{exam.title} marking scheme')
