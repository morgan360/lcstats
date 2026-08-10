"""Photograph-your-working endpoints.

Kept out of views.py because this is a self-contained flow across two devices,
and because none of it touches marking. Nothing here writes a score.

The shape of the flow, and why:

  laptop  POST work_slot        -> row in AWAITING_PHOTO, QR of a signed link
  phone   GET  work_mobile      -> minimal upload page, no login
  phone   POST work_mobile      -> store, analyse, return the commentary
  laptop  GET  work_status      -> polls until COMPLETE

The phone is not logged in. Requiring a login there would defeat the point of
the QR, so the token in the link is the authorisation: signed, short-lived, and
scoped to uploading one photo to one slot. It grants no read access.
"""
import base64
import io
import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.http import FileResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from exam_papers.models import ExamQuestionPart
from exam_papers.services.work_analysis import analyse_student_work
from interactive_lessons.models import QuestionPart

from .models import StudentProfile, WorkSubmission
from .services.image_intake import ImageIntakeError, encode_for_api, process_upload

logger = logging.getLogger(__name__)

TOKEN_SALT = "students.work_upload"

# Shown to a student when the analysis fails for any reason. Deliberately one
# fixed string: the exception text stays in the log, where it is useful, and
# out of the page, where it is noise at best and a leak at worst.
ANALYSIS_FAILED_MESSAGE = (
    "I couldn't read that one. Try again with the page flat, "
    "straight on, and in good light."
)


def _student(request):
    profile, _ = StudentProfile.objects.get_or_create(user=request.user)
    return profile


def _rate_limited(student):
    since = timezone.now() - timezone.timedelta(hours=1)
    used = WorkSubmission.objects.filter(student=student, created_at__gte=since).count()
    return used >= getattr(settings, "WORK_PHOTO_HOURLY_LIMIT", 20)


def _qr_data_uri(url):
    """PNG data URI of a QR for url, so no CDN or client-side library is needed."""
    import qrcode

    qr = qrcode.QRCode(box_size=8, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    buffer = io.BytesIO()
    qr.make_image(fill_color="black", back_color="white").save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()


def _analysis_payload(submission):
    """What both the phone and the laptop render."""
    return {
        "status": submission.status,
        "readable": submission.readable,
        "has_working": submission.has_working,
        "has_diagram": submission.has_diagram,
        "confidence": submission.confidence,
        "transcription": submission.transcription,
        "method_feedback": submission.method_feedback,
        "diagram_feedback": submission.diagram_feedback,
        "next_step": submission.next_step,
        "steps": (submission.analysis or {}).get("steps", []),
        "strengths": (submission.analysis or {}).get("strengths", []),
        "photo_url": reverse("work_photo", args=[submission.pk]),
    }


# ---------------------------------------------------------------------------
# Laptop side
# ---------------------------------------------------------------------------

@login_required
@require_POST
def work_slot(request):
    """Open a slot and return a QR pointing the phone at it."""
    # Checked here as well as in the template: hiding a button is not access
    # control, and this endpoint spends money on a vision call.
    if getattr(settings, "WORK_PHOTO_STAFF_ONLY", True) and not request.user.is_staff:
        return HttpResponseForbidden("Not available yet.")

    student = _student(request)
    if _rate_limited(student):
        return JsonResponse({
            "success": False,
            "message": "That's a lot of photos in one hour. Try again a bit later.",
        })

    part_type = request.POST.get("part_type")
    part_id = request.POST.get("part_id")

    kwargs = {}
    if part_type == "lesson":
        kwargs["question_part"] = get_object_or_404(QuestionPart, pk=part_id)
    elif part_type == "exam":
        kwargs["exam_question_part"] = get_object_or_404(ExamQuestionPart, pk=part_id)
    else:
        return JsonResponse({"success": False, "message": "Unknown question type."}, status=400)

    submission = WorkSubmission.objects.create(student=student, **kwargs)
    token = signing.dumps({"sub": submission.pk}, salt=TOKEN_SALT)
    url = request.build_absolute_uri(reverse("work_mobile", args=[token]))

    return JsonResponse({
        "success": True,
        "id": submission.pk,
        "upload_url": url,
        "qr": _qr_data_uri(url),
        "expires_in": getattr(settings, "WORK_UPLOAD_TOKEN_MAX_AGE", 900),
        "status_url": reverse("work_status", args=[submission.pk]),
    })


@login_required
@require_GET
def work_status(request, pk):
    """Poll target: has the photo arrived and been analysed yet?"""
    submission = get_object_or_404(WorkSubmission, pk=pk)
    if submission.student.user_id != request.user.id:
        return HttpResponseForbidden("Not yours.")

    payload = _analysis_payload(submission)
    payload["success"] = True
    if submission.status == WorkSubmission.Status.FAILED:
        payload["message"] = ANALYSIS_FAILED_MESSAGE
    return JsonResponse(payload)


@login_required
@require_GET
def work_photo(request, pk):
    """Serve a private photo, to its owner or staff only.

    The only route to these files. They are stored outside the directory the
    web server publishes, so without this view they are unreachable -- which is
    the point.
    """
    submission = get_object_or_404(WorkSubmission, pk=pk)
    if submission.student.user_id != request.user.id and not request.user.is_staff:
        return HttpResponseForbidden("Not yours.")
    if not submission.image:
        return HttpResponseForbidden("No photo.")

    response = FileResponse(submission.image.open("rb"), content_type="image/jpeg")
    response["Cache-Control"] = "private, no-store"
    return response


@login_required
@require_POST
def work_delete(request, pk):
    """Student-initiated deletion. The signal removes the file too."""
    submission = get_object_or_404(WorkSubmission, pk=pk)
    if submission.student.user_id != request.user.id:
        return HttpResponseForbidden("Not yours.")
    submission.delete()
    return JsonResponse({"success": True})


# ---------------------------------------------------------------------------
# Phone side -- no login, token only
# ---------------------------------------------------------------------------

def _submission_from_token(token):
    """Resolve an upload token, or return None with a reason.

    Returns (submission, error_message). A token is good for one photo: once
    the slot has moved off AWAITING_PHOTO, replaying it does nothing.
    """
    max_age = getattr(settings, "WORK_UPLOAD_TOKEN_MAX_AGE", 900)
    try:
        data = signing.loads(token, salt=TOKEN_SALT, max_age=max_age)
    except signing.SignatureExpired:
        return None, "This link has expired. Click the camera button again on your computer."
    except signing.BadSignature:
        return None, "That link isn't valid."

    submission = WorkSubmission.objects.filter(pk=data.get("sub")).first()
    if not submission:
        return None, "That link isn't valid."
    if submission.status != WorkSubmission.Status.AWAITING_PHOTO:
        return None, "A photo has already been sent for this question."
    return submission, None


@require_GET
def work_mobile(request, token):
    """The phone's upload page. Reached by scanning the QR, not by logging in."""
    submission, error = _submission_from_token(token)
    part = submission.part if submission else None
    prompt = ""
    if part is not None:
        prompt = getattr(part, "prompt", "") or ""

    return render(request, "students/work_mobile.html", {
        "token": token,
        "error": error,
        "submission": submission,
        "part_label": getattr(part, "label", "") if part else "",
        "prompt": prompt,
        "max_bytes": getattr(settings, "WORK_PHOTO_MAX_BYTES", 8 * 1024 * 1024),
    })


@csrf_exempt
@require_POST
def work_mobile_upload(request, token):
    """Store the photo and analyse it. Runs synchronously; the phone waits.

    CSRF-exempt because there is nothing for CSRF to protect: the phone has no
    session and sends no cookies, so the request carries no ambient authority
    to be forged. Authorisation is the signed token in the URL, which an
    attacker would have to already hold -- and which is good for one photo,
    into one slot, for fifteen minutes.
    """
    submission, error = _submission_from_token(token)
    if error:
        return JsonResponse({"success": False, "message": error}, status=400)

    if _rate_limited(submission.student):
        return JsonResponse({
            "success": False,
            "message": "That's a lot of photos in one hour. Try again a bit later.",
        })

    photo = request.FILES.get("photo")
    if not photo:
        return JsonResponse({"success": False, "message": "No photo came through."})

    try:
        content, width, height, size = process_upload(photo)
    except ImageIntakeError as e:
        # Student-safe by construction -- see image_intake.
        return JsonResponse({"success": False, "message": str(e)})

    submission.image.save(f"{submission.pk}.jpg", content, save=False)
    submission.image_width, submission.image_height = width, height
    submission.byte_size = size
    submission.status = WorkSubmission.Status.ANALYSING
    submission.save()

    try:
        result = _analyse(submission)
    except Exception as e:
        # The one place this could leak: keep the detail in the log, give the
        # student a fixed sentence. The photo is kept so they can retry.
        logger.exception("Work analysis failed for submission %s", submission.pk)
        submission.status = WorkSubmission.Status.FAILED
        submission.error_message = repr(e)
        submission.save(update_fields=["status", "error_message"])
        return JsonResponse({"success": False, "message": ANALYSIS_FAILED_MESSAGE})

    payload = _analysis_payload(submission)
    payload["success"] = True
    return JsonResponse(payload)


def _analyse(submission):
    """Run the vision call and flatten the result onto the row."""
    part = submission.part
    is_lesson = submission.question_part_id is not None

    if is_lesson:
        # QuestionPart.prompt is required, so it is always the question text.
        # (Question.text was removed back in migration 0003.)
        prompt = part.prompt
        question_image = part.image or part.question.image
        marking_scheme = None
        expected = part.answer or part.solution
    else:
        # Exam parts carry no question text -- it exists only as an image.
        prompt = "Shown in the question image below."
        question_image = getattr(part.question, "image", None)
        marking_scheme = part.solution_image
        expected = None

    result = analyse_student_work(
        encode_for_api(submission.image),
        question_prompt=prompt,
        part_label=part.label or "",
        question_image=question_image,
        marking_scheme_image=marking_scheme,
        expected_answer=expected,
    )

    submission.analysis = result
    submission.transcription = result.get("transcription", "") or ""
    submission.method_feedback = result.get("method_feedback", "") or ""
    submission.diagram_feedback = result.get("diagram_feedback", "") or ""
    submission.next_step = result.get("next_step", "") or ""
    submission.has_diagram = bool(result.get("has_diagram"))
    submission.has_working = bool(result.get("has_working", True))
    submission.readable = bool(result.get("readable", True))
    submission.confidence = (result.get("confidence") or "")[:8]
    submission.model_used = (result.get("model_used") or "")[:64]
    usage = result.get("usage", {})
    submission.prompt_tokens = usage.get("prompt_tokens", 0)
    submission.completion_tokens = usage.get("completion_tokens", 0)
    submission.status = WorkSubmission.Status.COMPLETE
    submission.analysed_at = timezone.now()
    submission.save()
    return result
