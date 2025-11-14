from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from .forms import ContactForm


def home(request):
    return render(request, "home/home.html")


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
