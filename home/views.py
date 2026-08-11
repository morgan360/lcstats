from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Count
from django.http import JsonResponse
from django.utils.safestring import mark_safe
import markdown
from .forms import ContactForm
from .models import NewsItem
from interactive_lessons.models import Topic, Question
from exam_papers.models import ExamPaper, ExamQuestion
from flashcards.models import Flashcard
from quickkicks.models import QuickKick
from core.models import Subject


def home(request):
    # Get total question count
    total_questions = Question.objects.count()

    # Get all active subjects with topic counts
    from django.db.models import Count as DBCount
    subjects = Subject.objects.filter(is_active=True).annotate(
        topic_count=DBCount('topics')
    )

    # Get topics with their question counts
    topics_with_counts = Topic.objects.annotate(
        question_count=Count('questions')
    ).filter(question_count__gt=0).order_by('-question_count')

    # Get active news items and render their markdown content
    news_items = NewsItem.get_active_for_user(request.user if request.user.is_authenticated else None)

    # Pre-render markdown to HTML for each news item
    for item in news_items:
        # Use markdown-katex extension if available, otherwise plain markdown
        try:
            item.content_html = mark_safe(
                markdown.markdown(
                    item.content,
                    extensions=['markdown_katex', 'fenced_code', 'tables', 'nl2br']
                )
            )
        except:
            # Fallback to basic markdown if markdown-katex is not available
            item.content_html = mark_safe(
                markdown.markdown(
                    item.content,
                    extensions=['fenced_code', 'tables', 'nl2br']
                )
            )

    context = {
        'subjects': subjects,
        'total_questions': total_questions,
        'topics_with_counts': topics_with_counts,
        'news_items': news_items,
    }

    # The marketing page quotes how much content is here, so the numbers come
    # from the database rather than a copywriter's guess. Only visitors see
    # that section, so only they pay for the counts.
    if not request.user.is_authenticated:
        context.update({
            'exam_paper_count': ExamPaper.objects.count(),
            'exam_question_count': ExamQuestion.objects.count(),
            'topic_count': topics_with_counts.count(),
            'flashcard_count': Flashcard.objects.count(),
            'quickkick_count': QuickKick.objects.count(),
        })

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


@login_required
def dismiss_news_item(request, news_id):
    """Allow students to dismiss news items (AJAX endpoint)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    news_item = get_object_or_404(NewsItem, id=news_id)

    # Check if dismissible
    if not news_item.is_dismissible:
        return JsonResponse({'error': 'This news item cannot be dismissed'}, status=403)

    # Add user to dismissed_by list
    news_item.dismissed_by.add(request.user)

    return JsonResponse({'success': True, 'message': 'News item dismissed'})
