from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LogoutView
from django.db.models import Avg, Count, Q
from django.contrib import messages
from django.http import HttpResponse
from django.utils import timezone
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
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
    """Generate and download a PDF report of question attempts by topic"""
    from io import BytesIO

    profile = StudentProfile.objects.get(user=request.user)

    # Get all attempts organized by topic
    attempts_by_topic = QuestionAttempt.objects.filter(student=profile).select_related(
        'question', 'question__topic'
    ).order_by('question__topic__name', '-attempted_at')

    # Create PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()

    # Title
    title = Paragraph(f"<b>Question Attempts by Topic</b>", styles['Heading1'])
    elements.append(title)
    elements.append(Spacer(1, 12))

    # Student info
    student_info = Paragraph(f"Student: {request.user.username}", styles['Normal'])
    elements.append(student_info)
    elements.append(Spacer(1, 20))

    # Group attempts by topic
    current_topic = None
    topic_data = []

    for attempt in attempts_by_topic:
        topic_name = attempt.question.topic.name if attempt.question.topic else 'No Topic'

        # If new topic, add previous topic's table and start new one
        if current_topic != topic_name:
            if topic_data:
                # Add previous topic's table
                elements.append(Paragraph(f"<b>{current_topic}</b>", styles['Heading2']))
                elements.append(Spacer(1, 6))

                table = Table(topic_data, colWidths=[100, 80, 250])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                elements.append(table)
                elements.append(Spacer(1, 20))

            # Start new topic
            current_topic = topic_name
            topic_data = [['Date', 'Result', 'Question']]

        # Add attempt to current topic
        date_str = attempt.attempted_at.strftime('%Y-%m-%d %H:%M')
        result = 'Correct' if attempt.is_correct else 'Wrong'
        question_text = attempt.question.text[:60] + '...' if len(attempt.question.text) > 60 else attempt.question.text
        topic_data.append([date_str, result, question_text])

    # Add final topic's table
    if topic_data and len(topic_data) > 1:
        elements.append(Paragraph(f"<b>{current_topic}</b>", styles['Heading2']))
        elements.append(Spacer(1, 6))

        table = Table(topic_data, colWidths=[100, 80, 250])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(table)

    # Build PDF
    doc.build(elements)
    buffer.seek(0)

    # Return as downloadable PDF
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    filename = f'question_attempts_{request.user.username}_{timezone.now().strftime("%Y%m%d")}.pdf'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
