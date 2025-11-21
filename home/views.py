from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta
from .forms import ContactForm
from interactive_lessons.models import Topic, Question
from students.models import UserSession


def home(request):
    # Get total question count
    total_questions = Question.objects.count()

    # Get topics with their question counts
    topics_with_counts = Topic.objects.annotate(
        question_count=Count('questions')
    ).filter(question_count__gt=0).order_by('-question_count')

    # Count active logged-in students
    # Consider a user "active" if they had activity in the last 3 hours
    activity_threshold = timezone.now() - timedelta(hours=3)
    active_users_count = UserSession.objects.filter(
        last_activity__gte=activity_threshold
    ).values('user').distinct().count()

    context = {
        'total_questions': total_questions,
        'topics_with_counts': topics_with_counts,
        'active_users_count': active_users_count,
    }
    return render(request, "home/home.html", context)


def about(request):
    """Display the about page"""
    return render(request, "home/about.html")


def contact(request):
    """Display and handle the contact form"""
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']
            subject = form.cleaned_data['subject']
            message = form.cleaned_data['message']

            # Construct email message
            full_message = f"""
Contact Form Submission from LCAI Maths

From: {name}
Email: {email}
Subject: {subject}

Message:
{message}
            """

            try:
                # Send email to admin
                send_mail(
                    subject=f"Contact Form: {subject}",
                    message=full_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[settings.DEFAULT_FROM_EMAIL],
                    fail_silently=False,
                )
                messages.success(request, "Thank you for your message! We'll get back to you soon.")
                return redirect('contact')
            except Exception as e:
                messages.error(request, "Sorry, there was an error sending your message. Please try again later.")
    else:
        form = ContactForm()

    return render(request, "home/contact.html", {"form": form})
