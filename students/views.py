from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LogoutView
from django.db.models import Avg, Count, Q
from django.contrib import messages
from django.http import HttpResponse
from django.utils import timezone
from .models import StudentProfile, RegistrationCode, QuestionAttempt
from .forms import SignupFormWithCode

# Signup view — handles registration with code validation
def signup_view(request):
    if request.method == 'POST':
        form = SignupFormWithCode(request.POST)
        if form.is_valid():
            # Save the user
            user = form.save()

            # Mark the registration code as used
            code = form.cleaned_data.get('registration_code')
            try:
                reg_code = RegistrationCode.objects.get(code=code)
                reg_code.use_code()
            except RegistrationCode.DoesNotExist:
                pass  # Already validated in form

            messages.success(request, 'Account created successfully! You can now log in.')
            return redirect('login')
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

    context = {
        "profile": profile,
        "accuracy": accuracy,
        "recent_attempts": attempts[:10],
        "topic_summary": topic_summary,
        "total_attempts": total_attempts,
    }
    return render(request, "students/dashboard.html", context)


class LogoutViewAllowGet(LogoutView):
    # ✅ allow GET at the dispatcher level
    http_method_names = ["get", "post", "head", "options"]

    def get(self, request, *args, **kwargs):
        # Treat GET like POST so it actually logs out
        return self.post(request, *args, **kwargs)


@login_required
def download_attempts_report(request):
    """Generate and download a report of all question attempts for the logged-in student"""
    profile = StudentProfile.objects.get(user=request.user)

    # Get all attempts for this student, ordered by most recent first
    attempts = QuestionAttempt.objects.filter(student=profile).select_related(
        'question', 'question__topic'
    ).order_by('-attempted_at')

    # Calculate statistics
    total_attempts = attempts.count()
    correct_attempts = attempts.filter(is_correct=True).count()
    accuracy = (correct_attempts / total_attempts * 100) if total_attempts > 0 else 0
    total_score = sum(a.score_awarded for a in attempts)
    avg_score = total_score / total_attempts if total_attempts > 0 else 0

    # Generate text report
    lines = []
    lines.append('=' * 80)
    lines.append('STUDENT QUESTION ATTEMPTS REPORT')
    lines.append('=' * 80)
    lines.append(f"Student: {request.user.get_full_name() or request.user.username}")
    lines.append(f"Username: {request.user.username}")
    lines.append(f"Generated: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append('')

    lines.append('-' * 80)
    lines.append('SUMMARY')
    lines.append('-' * 80)
    lines.append(f"Total Attempts: {total_attempts}")
    lines.append(f"Correct Answers: {correct_attempts}")
    lines.append(f"Accuracy: {accuracy:.1f}%")
    lines.append(f"Average Score: {avg_score:.1f}%")
    lines.append(f"Total Score: {total_score:.1f}")
    lines.append(f"Lessons Completed: {profile.lessons_completed}")
    lines.append('')

    if attempts:
        lines.append('-' * 80)
        lines.append('DETAILED QUESTION ATTEMPTS')
        lines.append('-' * 80)
        lines.append(f"{'Date/Time':<20} {'Topic':<20} {'Score':<8} {'Result':<8} {'Question'}")
        lines.append('-' * 80)

        for attempt in attempts:
            date_str = attempt.attempted_at.strftime('%Y-%m-%d %H:%M')
            topic = (attempt.question.topic.name if attempt.question.topic else 'N/A')[:19]
            score = f"{attempt.score_awarded:.1f}%"
            result = "Correct" if attempt.is_correct else "Wrong"
            question = attempt.question.text[:50]

            lines.append(f"{date_str:<20} {topic:<20} {score:<8} {result:<8} {question}")
    else:
        lines.append('No attempts recorded yet.')

    lines.append('')
    lines.append('=' * 80)
    lines.append('END OF REPORT')
    lines.append('=' * 80)

    report_text = '\n'.join(lines)

    # Return as downloadable text file
    response = HttpResponse(report_text, content_type='text/plain')
    filename = f'question_attempts_{request.user.username}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.txt'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
