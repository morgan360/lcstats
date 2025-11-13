from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LogoutView
from django.db.models import Avg, Count, Q
from django.contrib import messages
from .models import StudentProfile, RegistrationCode
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
