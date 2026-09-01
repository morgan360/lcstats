"""Teacher-side homework checking.

Access is layered the way the reports app does it: @teacher_required for the
group, then object-level ownership on every view, because a teacher must not
reach another teacher's class or a student who is not in one of their own.
"""
import json
import logging

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import FileResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from homework.models import TeacherClass
from hw_solutions.models import HWSolution
from students.decorators import teacher_required
from students.services.image_intake import ImageIntakeError, process_upload

from .models import CheckPhoto, HomeworkCheck, Rating
from .services import runner

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Ownership
# ---------------------------------------------------------------------------

def _owned_classes(request):
    """Every class this teacher may act on."""
    if request.user.is_superuser:
        return TeacherClass.objects.filter(is_active=True)
    profile = getattr(request.user, 'teacher_profile', None)
    if profile is None:
        raise PermissionDenied
    return profile.classes.filter(is_active=True)


def _get_owned_check(request, pk):
    check = get_object_or_404(
        HomeworkCheck.objects.select_related(
            'student', 'teacher_class', 'solution'),
        pk=pk,
    )
    if request.user.is_superuser:
        return check
    profile = getattr(request.user, 'teacher_profile', None)
    if profile is None or check.teacher_class.teacher_id != profile.pk:
        raise PermissionDenied
    return check


def _rate_limited(user):
    since = timezone.now() - timezone.timedelta(hours=1)
    used = HomeworkCheck.objects.filter(
        teacher=user, created_at__gte=since).count()
    return used >= getattr(settings, 'HOMEWORK_CHECK_HOURLY_LIMIT', 40)


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

@teacher_required
@require_GET
def index(request):
    """Recent checks, optionally narrowed to one class."""
    classes = _owned_classes(request)
    checks = HomeworkCheck.objects.filter(
        teacher_class__in=classes
    ).select_related('student', 'teacher_class', 'solution')

    class_id = request.GET.get('class')
    current_class = None
    if class_id and class_id.isdigit():
        current_class = classes.filter(pk=int(class_id)).first()
        if current_class:
            checks = checks.filter(teacher_class=current_class)

    return render(request, 'homework_check/index.html', {
        'checks': checks[:60],
        'classes': classes,
        'current_class': current_class,
    })


@teacher_required
def check_new(request):
    """Pick a student, name the exercise, choose the solutions to check against."""
    classes = _owned_classes(request)

    solutions = HWSolution.objects.select_related('subject')
    current_subject = getattr(request, 'current_subject', None)
    if current_subject:
        solutions = solutions.filter(
            Q(subject=current_subject) | Q(subject__isnull=True))

    if request.method == 'POST':
        if _rate_limited(request.user):
            messages.error(
                request,
                "That's a lot of checks in one hour. Try again a bit later.")
            return redirect('homework_check:index')

        teacher_class = get_object_or_404(classes, pk=request.POST.get('teacher_class'))
        student = get_object_or_404(
            teacher_class.students, pk=request.POST.get('student'))
        solution = get_object_or_404(solutions, pk=request.POST.get('solution'))
        exercise = (request.POST.get('exercise_name') or '').strip()

        if not exercise:
            messages.error(request, "Give the exercise a name so you can find it later.")
        else:
            check = HomeworkCheck.objects.create(
                teacher=request.user,
                teacher_class=teacher_class,
                student=student,
                solution=solution,
                exercise_name=exercise[:200],
                solution_pages=(request.POST.get('solution_pages') or '').strip()[:60],
            )
            return redirect('homework_check:check_detail', pk=check.pk)

    selected_class = None
    class_id = request.GET.get('class')
    if class_id and class_id.isdigit():
        selected_class = classes.filter(pk=int(class_id)).first()

    return render(request, 'homework_check/check_new.html', {
        'classes': classes,
        'solutions': solutions,
        'selected_class': selected_class,
        'current_subject': current_subject,
    })


@teacher_required
@require_GET
def check_detail(request, pk):
    check = _get_owned_check(request, pk)
    done, total = check.progress()
    return render(request, 'homework_check/check_detail.html', {
        'check': check,
        'photos': check.photos.all(),
        'done': done,
        'total': total,
        'max_photos': getattr(settings, 'HOMEWORK_CHECK_MAX_PHOTOS', 16),
        'ratings': Rating.choices,
    })


@teacher_required
@require_GET
def report_print(request, pk):
    """The one-page sheet handed back to the student."""
    check = _get_owned_check(request, pk)
    return render(request, 'homework_check/report_print.html', {
        'check': check,
        'questions': check.findings or [],
    })


# ---------------------------------------------------------------------------
# Photos
# ---------------------------------------------------------------------------

@teacher_required
@require_POST
def check_upload(request, pk):
    """Store one photo. The page posts these one at a time.

    Sequentially, deliberately: sixteen full-resolution decodes held in a
    phone's memory at once will have Safari kill the tab.
    """
    check = _get_owned_check(request, pk)

    limit = getattr(settings, 'HOMEWORK_CHECK_MAX_PHOTOS', 16)
    if check.photos.count() >= limit:
        return JsonResponse({
            'success': False,
            'message': f"That's the limit of {limit} photos for one exercise.",
        })

    photo = request.FILES.get('photo')
    if not photo:
        return JsonResponse({'success': False, 'message': 'No photo came through.'})

    try:
        content, width, height, size = process_upload(photo)
    except ImageIntakeError as e:
        # Written to be read by a person -- see image_intake.
        return JsonResponse({'success': False, 'message': str(e)})

    order = check.photos.count()
    row = CheckPhoto(hw_check=check, order=order,
                     image_width=width, image_height=height, byte_size=size)
    row.image.save(f"{order}.jpg", content, save=False)
    row.save()

    return JsonResponse({
        'success': True,
        'id': row.pk,
        'order': order,
        'url': f"/homework-check/photo/{row.pk}/",
        'count': check.photos.count(),
    })


@teacher_required
@require_GET
def check_photo(request, pk):
    """Serve a private photo to a teacher who owns the class.

    The only route to these files. They are stored outside the directory the
    web server publishes, so without this view they are unreachable -- which
    is the point.
    """
    photo = get_object_or_404(
        CheckPhoto.objects.select_related('hw_check__teacher_class'), pk=pk)
    _get_owned_check(request, photo.hw_check_id)

    if not photo.image:
        return HttpResponseForbidden("No photo.")

    response = FileResponse(photo.image.open("rb"), content_type="image/jpeg")
    response["Cache-Control"] = "private, no-store"
    return response


@teacher_required
@require_POST
def photo_delete(request, pk):
    """Drop one photo, so a bad one can be retaken without losing the rest."""
    photo = get_object_or_404(
        CheckPhoto.objects.select_related('hw_check__teacher_class'), pk=pk)
    check = _get_owned_check(request, photo.hw_check_id)
    photo.delete()

    # Keep the ordering contiguous so the chunk labels stay honest.
    for index, row in enumerate(check.photos.all()):
        if row.order != index:
            CheckPhoto.objects.filter(pk=row.pk).update(order=index)

    return JsonResponse({'success': True, 'count': check.photos.count()})


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

@teacher_required
@require_POST
def analyse_next(request, pk):
    """Run exactly one chunk. The page calls this until 'complete' comes back."""
    check = _get_owned_check(request, pk)

    if not check.photos.exists():
        return JsonResponse({'success': False, 'message': 'No photos yet.'})

    try:
        done, total = runner.analyse_next_chunk(check)
    except Exception as e:
        logger.exception("Homework check %s failed during analysis", check.pk)
        check.status = HomeworkCheck.Status.FAILED
        check.error_message = repr(e)
        check.save(update_fields=['status', 'error_message'])
        return JsonResponse({
            'success': False,
            'message': runner.ANALYSIS_FAILED_MESSAGE,
        })

    complete = done >= total
    if complete:
        runner.finalise(check)

    return JsonResponse({
        'success': True,
        'done': done,
        'total': total,
        'complete': complete,
    })


@teacher_required
@require_POST
def check_edit(request, pk):
    """Save a teacher's edit: a question comment, the summary, or the rating.

    Handing a student AI-written commentary the teacher has not been able to
    correct is the main risk this feature carries. This is the mitigation, so
    every field on the printed sheet has to be reachable from here.
    """
    check = _get_owned_check(request, pk)

    try:
        data = json.loads(request.body)
    except (ValueError, TypeError):
        return JsonResponse({'success': False, 'message': 'Bad request.'}, status=400)

    field = data.get('field')
    value = data.get('value', '')

    if field == 'summary':
        check.summary = str(value)[:2000]
        check.save(update_fields=['summary'])

    elif field == 'teacher_note':
        check.teacher_note = str(value)[:2000]
        check.save(update_fields=['teacher_note'])

    elif field == 'rating':
        value = str(value)
        if value and value not in dict(Rating.choices):
            return JsonResponse({'success': False, 'message': 'Unknown rating.'},
                                status=400)
        check.teacher_rating = value
        check.save(update_fields=['teacher_rating'])

    elif field == 'comment':
        label = str(data.get('label', ''))
        findings = list(check.findings or [])
        for row in findings:
            if row.get('label') == label:
                row['comment'] = str(value)[:1000]
                break
        else:
            return JsonResponse({'success': False, 'message': 'No such question.'},
                                status=400)
        check.findings = findings
        check.save(update_fields=['findings'])

    elif field == 'drop_question':
        label = str(data.get('label', ''))
        check.findings = [r for r in (check.findings or [])
                          if r.get('label') != label]
        check.save(update_fields=['findings'])

    else:
        return JsonResponse({'success': False, 'message': 'Unknown field.'},
                            status=400)

    if not check.reviewed_at:
        check.reviewed_at = timezone.now()
        check.save(update_fields=['reviewed_at'])

    return JsonResponse({'success': True})


@teacher_required
@require_POST
def check_delete(request, pk):
    check = _get_owned_check(request, pk)
    check.delete()
    messages.success(request, "Check deleted.")
    return redirect('homework_check:index')
