"""Teacher-side homework checking.

Access is layered the way the reports app does it: @teacher_required for the
group, then object-level ownership on every view, because a teacher must not
reach another teacher's class or a student who is not in one of their own.
"""
import hmac
import json
import logging
import re

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import FileResponse, Http404, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from homework.models import TeacherClass
from hw_solutions.models import HWSolution
from hw_solutions.services import build_sections
from students.decorators import teacher_required
from students.services.image_intake import ImageIntakeError, process_upload

from .models import CheckPhoto, HomeworkCheck, InboundScan, Rating, ScanAddress
from .services import runner, scans as scan_service

logger = logging.getLogger(__name__)

PHOTOS_DELETED_MESSAGE = (
    "The photos for this check have been deleted, so it can't take new ones "
    "or be marked again. Start a new check for this student instead."
)


# ---------------------------------------------------------------------------
# Ownership
# ---------------------------------------------------------------------------

def _owned_classes(request):
    """Every class this teacher may act on.

    Permissive for superusers on purpose -- this backs the permission checks,
    and an admin must still be able to reach a class to support a colleague.
    What the *pickers* offer is a narrower question; see _pickable_classes.
    """
    if request.user.is_superuser:
        return TeacherClass.objects.filter(is_active=True)
    profile = getattr(request.user, 'teacher_profile', None)
    if profile is None:
        raise PermissionDenied
    return profile.classes.filter(is_active=True)


def _pickable_classes(request):
    """What the class dropdown offers -- your own classes, not everyone's.

    A superuser is allowed to reach every class, but defaulting the picker to
    that put three other teachers' classes, from other schools, in the list
    beside their own. That is noise at best and the wrong student at worst.
    Their own classes come first; ?all=1 restores the full list, and an admin
    with no classes of their own still sees everything rather than nothing.
    """
    profile = getattr(request.user, 'teacher_profile', None)
    own = profile.classes.filter(is_active=True) if profile else TeacherClass.objects.none()

    if not request.user.is_superuser:
        if profile is None:
            raise PermissionDenied
        return own

    if request.GET.get('all') == '1' or not own.exists():
        return TeacherClass.objects.filter(is_active=True)
    return own


SIXTH_YEAR = re.compile(r'6th|sixth', re.IGNORECASE)


def _selected_class(request, classes):
    """The class a picker opens on: ?class= if given, else the 6th Years.

    Classes sort by name, so with no default the dropdown opened on 4th Year,
    and it is the Leaving Certs whose homework gets checked. Matched by name
    because TeacherClass has no year field; no match leaves the browser's own
    default, the first option.
    """
    class_id = request.GET.get('class')
    if class_id and class_id.isdigit():
        chosen = classes.filter(pk=int(class_id)).first()
        if chosen:
            return chosen
    return next((c for c in classes if SIXTH_YEAR.search(c.name)), None)


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
    classes = _pickable_classes(request)
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
        'scans_waiting': InboundScan.objects.filter(teacher=request.user).count(),
    })


# What a row on the student page says about a report, in this order. Correct
# answers lead; the rest only appear when there are some.
COUNT_PHRASES = [
    ('correct', 'right', 'right'),
    ('slip', 'slip', 'slips'),
    ('wrong', 'wrong', 'wrong'),
    ('incomplete', 'incomplete', 'incomplete'),
    ('not_in_solutions', 'not in the solutions', 'not in the solutions'),
]


def _count_line(counts):
    """ "12 questions: 10 right, 2 slips" -- or '' before a check is marked."""
    total = (counts or {}).get('total') or 0
    if not total:
        return ''
    parts = []
    for key, one, many in COUNT_PHRASES:
        n = counts.get(key) or 0
        if n or key == 'correct':
            parts.append(f"{n} {one if n == 1 else many}")
    return f"{total} question{'s' if total != 1 else ''}: {', '.join(parts)}"


@teacher_required
@require_GET
def student_reports(request, student_id):
    """Every report for one student, newest first -- their homework history.

    The list page shows only the latest sixty checks, so a student's older
    reports drop off it within a couple of homeworks. They are kept for good
    (the purge takes photos, not reports), and this is where they stay
    reachable.

    Who may look follows reports.student_report: a student in one of your
    classes. Checks are then narrowed to your own classes, the same test
    _get_owned_check applies to each one, so another teacher's reports on a
    shared student never show here. Having checked a student also counts, so
    one who has since left the class keeps their history.
    """
    student = get_object_or_404(User, pk=student_id)
    checks = HomeworkCheck.objects.filter(student=student).select_related(
        'teacher_class', 'solution')

    if not request.user.is_superuser:
        profile = getattr(request.user, 'teacher_profile', None)
        if profile is None:
            raise PermissionDenied
        checks = checks.filter(teacher_class__teacher=profile)
        in_class = profile.classes.filter(students=student).exists()
        if not in_class and not checks.exists():
            raise PermissionDenied

    checks = list(checks)
    for check in checks:
        check.count_line = _count_line(check.counts)

    tally = {}
    for check in checks:
        if check.final_rating:
            tally[check.final_rating] = tally.get(check.final_rating, 0) + 1

    return render(request, 'homework_check/student.html', {
        'student': student,
        'checks': checks,
        'classes': sorted({c.teacher_class.name for c in checks}),
        'tally': [(label, tally[value]) for value, label in Rating.choices
                  if value in tally],
    })


def _solutions_for(request, index=True):
    """The solution PDFs a teacher may pick, for the subject they are in.

    Shared by the new-check form and the scans page, so both offer the same
    list. ``index`` builds the exercise list of any PDF not yet indexed, so one
    uploaded through the admin needs no extra step; it reads the text layer
    only -- cheap, and cached after the first time.
    """
    solutions = HWSolution.objects.select_related('subject').prefetch_related('sections')
    current_subject = getattr(request, 'current_subject', None)
    if current_subject:
        solutions = solutions.filter(
            Q(subject=current_subject) | Q(subject__isnull=True))

    if index:
        for solution in solutions:
            if not solution.sections.all():
                try:
                    build_sections(solution)
                except Exception:
                    logger.exception("Could not index solution %s", solution.pk)
    return solutions


@teacher_required
def check_new(request):
    """Pick a student, name the exercise, choose the solutions to check against."""
    classes = _pickable_classes(request)
    solutions = _solutions_for(request)
    current_subject = getattr(request, 'current_subject', None)

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

    selected_class = _selected_class(request, classes)

    return render(request, 'homework_check/check_new.html', {
        'classes': classes,
        'solutions': solutions,
        'selected_class': selected_class,
        'carried': _carried_over(request, classes, solutions, selected_class),
        'current_subject': current_subject,
        'max_solution_pages': getattr(
            settings, 'HOMEWORK_CHECK_MAX_SOLUTION_PAGES', 30),
    })


def _carried_over(request, classes, solutions, selected_class):
    """The settings brought forward from a finished check, if any.

    Marking a class is a stack of copies, not one: the class, the exercise
    name, the solutions PDF and the page range are the same for all
    twenty-five, and only the student and the photographs change. The
    "check another student" button on a finished report sends those four
    back here as query parameters so they are already filled in.

    Every one of them is re-checked against what this teacher may actually
    pick, because they arrive in a URL a teacher can edit. The solution is
    looked up in the same queryset the dropdown is built from; the class was
    already narrowed by the caller. Nothing here grants access -- picking a
    student still goes through the class the POST handler validates.
    """
    solution = None
    solution_id = request.GET.get('solution')
    if solution_id and solution_id.isdigit():
        solution = solutions.filter(pk=int(solution_id)).first()

    exercise = (request.GET.get('exercise') or '').strip()[:200]
    pages = (request.GET.get('pages') or '').strip()[:60]

    if not (solution or exercise or pages):
        return None

    return {
        'class_id': selected_class.pk if selected_class else None,
        'solution_id': solution.pk if solution else None,
        'exercise_name': exercise,
        'pages': pages,
    }


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
        'photo_retention_days': getattr(
            settings, 'HOMEWORK_CHECK_PHOTO_RETENTION_DAYS', 7),
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

    # New pages on a check whose originals are gone would be marked against a
    # report built from different photos. A fresh check is the honest route.
    if check.photos_deleted:
        return JsonResponse({'success': False, 'message': PHOTOS_DELETED_MESSAGE})

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

    if check.photos_deleted:
        return JsonResponse({'success': False, 'message': PHOTOS_DELETED_MESSAGE})
    if not check.photos.exists():
        return JsonResponse({'success': False, 'message': 'No photos yet.'})

    try:
        done, total = runner.analyse_next_chunk(check)
    except runner.EmptyResponse as e:
        # Not a broken check: the photos are untouched and still pending, so
        # pressing the button again picks up the same batch.
        logger.warning("Homework check %s: empty model response", check.pk)
        return JsonResponse({'success': False, 'message': str(e)})
    except runner.Stalled as e:
        # The photos are untouched and still pending, so the button picks up
        # the same batch. Not logged as a failure: nothing here is broken.
        logger.warning("Homework check %s: batch timed out", check.pk)
        return JsonResponse({'success': False, 'message': str(e)})
    except runner.TooManySolutionPages as e:
        # The teacher's to fix, not a failure to log: leave the check alone so
        # they can narrow the range and press the button again.
        return JsonResponse({'success': False, 'message': str(e)})
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
    """Delete one check, from either the list or the check's own page.

    The photographs go with it: CheckPhoto cascades, and its post_delete
    receiver takes each file off disk. There is no undo, which is why both
    callers confirm first and name the student in the prompt.
    """
    check = _get_owned_check(request, pk)
    label = f"{check.student.get_full_name() or check.student.username} — {check.exercise_name}"
    check.delete()
    messages.success(request, f"Deleted {label}.")

    # Deleting from a class-filtered list should leave you on that same list
    # rather than back at all classes, which is where the next one to delete
    # almost certainly is. Digits only -- it is a form field, not a trusted one.
    class_id = request.POST.get('class', '')
    if class_id.isdigit():
        return redirect(f"{reverse('homework_check:index')}?class={class_id}")
    return redirect('homework_check:index')


# ---------------------------------------------------------------------------
# Scans by email
# ---------------------------------------------------------------------------

@csrf_exempt
@require_POST
def inbound_email(request):
    """Take one raw email from the Cloudflare Email Worker.

    Not a page anyone visits, so it answers the Worker only. With no secret
    configured, or the wrong one, it is a 404 -- indistinguishable from there
    being no endpoint at all. An address that matches no teacher is accepted
    and dropped, so the response never confirms which tokens exist.

    The body is read with request.read(), not request.body: body refuses
    anything over DATA_UPLOAD_MAX_MEMORY_SIZE (2.5MB), and a scanned class
    set is routinely ten times that.
    """
    secret = getattr(settings, 'HOMEWORK_CHECK_INBOUND_SECRET', '')
    given = request.headers.get('X-Scan-Secret', '')
    if not secret or not hmac.compare_digest(given.encode(), secret.encode()):
        raise Http404

    limit = getattr(settings, 'HOMEWORK_CHECK_INBOUND_MAX_BYTES', 26 * 1024 * 1024)
    try:
        length = int(request.META.get('CONTENT_LENGTH') or 0)
    except ValueError:
        length = 0
    if length <= 0 or length > limit:
        return JsonResponse({'ok': False, 'message': 'Too large.'}, status=413)

    teacher = scan_service.teacher_for_recipient(request.headers.get('X-Scan-To', ''))
    if teacher is None:
        return JsonResponse({'ok': True, 'stored': 0})

    raw = request.read(limit + 1)
    try:
        stored = scan_service.store_email(teacher, raw)
    except Exception:
        # A 500 makes the Worker bounce the email, so the sender learns it did
        # not arrive -- better than a scan silently going nowhere.
        logger.exception("Could not store an emailed scan for %s", teacher.pk)
        return JsonResponse({'ok': False, 'message': 'Could not store it.'}, status=500)

    logger.info("Stored %s scan(s) by email for teacher %s", stored, teacher.pk)
    return JsonResponse({'ok': True, 'stored': stored})


def _own_scans(request):
    return InboundScan.objects.filter(teacher=request.user)


@teacher_required
@require_GET
def scans(request):
    """Emailed scans waiting to be matched to students."""
    classes = _pickable_classes(request)
    solutions = _solutions_for(request)
    selected_class = _selected_class(request, classes)

    return render(request, 'homework_check/scans.html', {
        'address': ScanAddress.for_teacher(request.user),
        'scans': _own_scans(request),
        'classes': classes,
        'solutions': solutions,
        'selected_class': selected_class,
        'carried': None,
        'max_solution_pages': getattr(
            settings, 'HOMEWORK_CHECK_MAX_SOLUTION_PAGES', 30),
        'photo_retention_days': getattr(
            settings, 'HOMEWORK_CHECK_PHOTO_RETENTION_DAYS', 7),
    })


@teacher_required
@require_POST
def scans_assign(request):
    """Make a check from every scan a student was picked for.

    One form for the whole class: the exercise and solutions are chosen once,
    and each scan carries its own student. Scans left on "skip" stay waiting.
    Only this teacher's scans are ever looked at, whatever ids the form sends.
    """
    classes = _pickable_classes(request)
    teacher_class = get_object_or_404(classes, pk=request.POST.get('teacher_class'))
    solution = get_object_or_404(
        _solutions_for(request, index=False), pk=request.POST.get('solution'))
    exercise = (request.POST.get('exercise_name') or '').strip()
    pages = (request.POST.get('solution_pages') or '').strip()

    if not exercise:
        messages.error(request, "Give the exercise a name so you can find it later.")
        return redirect('homework_check:scans')

    roster = {str(s.pk): s for s in teacher_class.students.all()}
    created, failed = [], 0
    for scan in _own_scans(request).filter(problem=''):
        student = roster.get(request.POST.get(f'student_{scan.pk}', ''))
        if student is None:
            continue
        try:
            check = scan_service.create_check_from_scan(
                scan, teacher=request.user, teacher_class=teacher_class,
                student=student, solution=solution, exercise_name=exercise,
                solution_pages=pages,
            )
        except ImageIntakeError as e:
            scan.problem = str(e)[:200]
            scan.save(update_fields=['problem'])
            failed += 1
            continue
        created.append(check.pk)

    if failed:
        messages.error(request, f"{failed} scan(s) couldn't be read — the reason is shown on each.")
    if not created:
        if not failed:
            messages.error(request, "Pick a student beside at least one scan.")
        return redirect('homework_check:scans')

    messages.success(request, f"Made {len(created)} check(s). Press “Check all” to mark them.")
    ids = ','.join(str(pk) for pk in created)
    return redirect(f"{reverse('homework_check:run')}?ids={ids}")


@teacher_required
@require_GET
def scan_thumb(request, pk):
    """A scan's first page, to its own teacher only. Private, like the photos."""
    scan = get_object_or_404(_own_scans(request), pk=pk)
    if not scan.thumbnail:
        raise Http404
    response = FileResponse(scan.thumbnail.open("rb"), content_type="image/jpeg")
    response["Cache-Control"] = "private, no-store"
    return response


@teacher_required
@require_POST
def scan_delete(request, pk):
    """Discard a scan that isn't wanted. Its files go with it."""
    get_object_or_404(_own_scans(request), pk=pk).delete()
    messages.success(request, "Scan discarded.")
    return redirect('homework_check:scans')


@teacher_required
@require_GET
def run(request):
    """Mark a batch of checks one after another, from one page.

    The checks made from a class's scans, in the order they were made. The
    page drives the same analyse-next endpoint the check page does, one check
    at a time, so nothing about the marking itself differs.
    """
    ids = [int(i) for i in (request.GET.get('ids') or '').split(',') if i.isdigit()]
    checks = HomeworkCheck.objects.filter(pk__in=ids).select_related(
        'student', 'teacher_class')
    if not request.user.is_superuser:
        profile = getattr(request.user, 'teacher_profile', None)
        if profile is None:
            raise PermissionDenied
        checks = checks.filter(teacher_class__teacher=profile)

    order = {pk: n for n, pk in enumerate(ids)}
    checks = sorted(checks, key=lambda c: order.get(c.pk, 0))
    if not checks:
        raise Http404

    rows = []
    for check in checks:
        done, total = check.progress()
        rows.append({'check': check, 'done': done, 'total': total})
    return render(request, 'homework_check/run.html', {'rows': rows})
