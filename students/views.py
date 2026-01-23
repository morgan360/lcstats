from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LogoutView
from django.db.models import Avg, Count, Q
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import StudentProfile, RegistrationCode
from .forms import SignupFormWithCode

# Signup view — handles registration with code validation
def signup_view(request):
    if request.method == 'POST':
        form = SignupFormWithCode(request.POST)
        if form.is_valid():
            # Save the user (form.save() handles staff status and class enrollment)
            user = form.save(request)

            # Get registration code to provide appropriate success message
            code = form.cleaned_data.get('registration_code')
            try:
                reg_code = RegistrationCode.objects.get(code=code)
                if reg_code.code_type == 'teacher':
                    messages.success(request, 'Teacher account created successfully! You can now log in and access the teacher dashboard.')
                else:
                    messages.success(request, 'Student account created successfully! You can now log in and start learning.')
            except RegistrationCode.DoesNotExist:
                messages.success(request, 'Account created successfully! You can now log in.')

            return redirect('account_login')
    else:
        form = SignupFormWithCode()
    return render(request, 'students/signup.html', {'form': form})


# Dashboard view — shows student profile info (requires login)
@login_required
def dashboard_view(request):
    # Ensure profile exists for the logged-in user
    profile, _ = StudentProfile.objects.get_or_create(user=request.user)

    # Retrieve all attempts, newest first
    attempts = profile.attempts.select_related("question").order_by("-attempted_at")

    # --- Overall accuracy ---
    total_attempts = attempts.count()
    correct_attempts = attempts.filter(is_correct=True).count()
    accuracy = round((correct_attempts / total_attempts) * 100, 1) if total_attempts else 0

    # --- Topic-wise performance summary ---
    topic_summary = (
        profile.attempts
        .values("question__topic__name")  # ✅ uses topic name from interactive_lessons
        .annotate(
            avg_score=Avg("score_awarded"),
            attempts=Count("id"),
            correct=Count("id", filter=Q(is_correct=True)),
        )
        .order_by("question__topic__name")
    )

    # Update profile totals
    profile.update_progress()

    # --- Homework summary and notifications ---
    try:
        from homework.views import get_homework_summary
        from homework.models import HomeworkNotificationSnooze

        # Get comprehensive homework summary
        homework_summary = get_homework_summary(request.user)

        # Check if notifications are snoozed
        try:
            snooze = HomeworkNotificationSnooze.objects.get(student=request.user)
            show_notification_modal = homework_summary['has_homework'] and not snooze.is_active()
        except HomeworkNotificationSnooze.DoesNotExist:
            show_notification_modal = homework_summary['has_homework']

        homework_count = homework_summary['total_count']
        upcoming_homework = homework_summary['due_soon'][:3]
        overdue_homework = homework_summary['overdue'][:3]
    except Exception as e:
        homework_count = 0
        upcoming_homework = []
        overdue_homework = []
        homework_summary = {}
        show_notification_modal = False

    context = {
        "profile": profile,
        "accuracy": accuracy,
        "recent_attempts": attempts[:10],
        "topic_summary": topic_summary,
        "total_attempts": total_attempts,
        "homework_count": homework_count,
        "upcoming_homework": upcoming_homework,
        "overdue_homework": overdue_homework,
        "homework_summary": homework_summary,
        "show_notification_modal": show_notification_modal,
    }
    return render(request, "students/dashboard.html", context)


class LogoutViewAllowGet(LogoutView):
    """
    Custom logout view that allows GET requests (for simple link-based logout)
    """
    http_method_names = ["get", "post", "head", "options"]

    def get(self, request, *args, **kwargs):
        """Handle GET request by performing logout and redirecting"""
        from django.contrib.auth import logout
        from django.shortcuts import resolve_url
        from django.http import HttpResponseRedirect

        # Perform logout
        logout(request)

        # Get redirect URL from next_page attribute or use default
        next_page = self.next_page or self.get_success_url()
        next_page = resolve_url(next_page)

        return HttpResponseRedirect(next_page)


@login_required
@require_POST
def question_attempt_feedback(request, attempt_id):
    """Submit feedback (thumbs up/down) for a question attempt's grading feedback."""
    import json
    from .models import QuestionFeedback, QuestionAttempt

    try:
        data = json.loads(request.body)
        feedback_type = data.get("feedback_type")  # 'helpful' or 'not_helpful'

        if feedback_type not in ['helpful', 'not_helpful']:
            return JsonResponse({"success": False, "error": "Invalid feedback type"}, status=400)

        # Get the attempt and verify it belongs to the current user
        attempt = get_object_or_404(QuestionAttempt, id=attempt_id, student__user=request.user)

        # Create or update feedback
        feedback, created = QuestionFeedback.objects.update_or_create(
            attempt=attempt,
            user=request.user,
            defaults={'feedback_type': feedback_type}
        )

        return JsonResponse({
            "success": True,
            "message": "Thanks for your feedback!",
            "feedback_type": feedback_type
        })
    except Exception as e:
        print(f"[Question Attempt Feedback Error] {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)
