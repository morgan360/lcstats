from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import JsonResponse
from django.utils import timezone
from django.contrib import messages
from django.utils.safestring import mark_safe
import markdown
from interactive_lessons.models import Topic
from interactive_lessons.services.marking import grade_submission
from interactive_lessons.views import render_math_markdown
from students.models import QuestionAttempt
from .models import QuickKick, QuickKickView


@login_required
def quickkicks_index(request):
    """
    Display all QuickKick videos across all topics.
    """
    quickkicks = QuickKick.objects.select_related('topic').order_by('topic__name', 'order', 'title')

    context = {
        'quickkicks': quickkicks,
    }
    return render(request, 'quickkicks/index.html', context)


@login_required
def quickkicks_list(request, topic_slug):
    """
    Display all QuickKick videos for a specific topic.
    Replaces the Revision column in interactive lessons.
    """
    topic = get_object_or_404(Topic, slug=topic_slug)
    quickkicks = QuickKick.objects.filter(topic=topic).order_by('order', 'title')

    context = {
        'topic': topic,
        'quickkicks': quickkicks,
    }
    return render(request, 'quickkicks/quickkicks_list.html', context)


@login_required
def quickkick_view(request, topic_slug, quickkick_id):
    """
    Display a single QuickKick video for watching.
    Records the view for homework tracking.
    If a test question is attached, shows it after video using the standard quiz interface.
    """
    topic = get_object_or_404(Topic, slug=topic_slug)
    quickkick = get_object_or_404(QuickKick, id=quickkick_id, topic=topic)

    # Get or create the view record
    view_record, created = QuickKickView.objects.get_or_create(
        user=request.user,
        quickkick=quickkick
    )

    # If no question attached, just show the video/applet
    if not quickkick.question:
        context = {
            'topic': topic,
            'quickkick': quickkick,
            'view_record': view_record,
        }
        return render(request, 'quickkicks/quickkick_view.html', context)

    # Question attached - use quiz interface
    question = quickkick.question
    parts = question.parts.all().order_by("order")

    results = {}
    student_answers = {}
    completed_parts = set()

    # Handle POST - grade a single QuestionPart
    if request.method == "POST":
        part_id = request.POST.get("part_id")
        if part_id:
            from interactive_lessons.models import QuestionPart
            part = get_object_or_404(QuestionPart, id=part_id)
            answer = request.POST.get(f"answer_{part.id}", "").strip()
            student_answers[part.id] = answer

            if answer:
                # Grade the submission
                result = grade_submission(
                    question_part_id=part.id,
                    student_answer=answer,
                    hint_used=False,
                    solution_used=False,
                ) or {}

                results[part.id] = result
                completed_parts.add(part.id)

                # Save attempt for progress tracking
                try:
                    QuestionAttempt.objects.create(
                        student=request.user.studentprofile,
                        question=part.question,
                        question_part=part,
                        student_answer=answer,
                        score_awarded=result.get("score", 0),
                        is_correct=result.get("is_correct", False),
                    )
                except Exception as e:
                    print(f"[Progress Tracking Error] {e}")

                # Update QuickKickView tracking
                try:
                    view_record.answer_submitted = True
                    view_record.answer_correct = result.get("is_correct", False)
                    view_record.score_awarded = result.get("score", 0)
                    view_record.attempts += 1
                    view_record.last_attempt_at = timezone.now()
                    view_record.save()
                except Exception as e:
                    print(f"[QuickKickView Tracking Error] {e}")

                # AJAX JSON feedback response
                if request.headers.get("x-requested-with") == "XMLHttpRequest":
                    return JsonResponse({
                        "is_correct": result.get("is_correct", False),
                        "score": result.get("score", 0),
                        "feedback": result.get("feedback", ""),
                        "hint": result.get("hint", ""),
                    })

    # Render question and part content (Math/KaTeX compatible)
    question.hint = render_math_markdown(question.hint)
    for part in parts:
        part.prompt = render_math_markdown(part.prompt)
        part.expected_format = render_math_markdown(part.expected_format or "")
        part.solution = render_math_markdown(part.solution or "")

    question.solution = render_math_markdown(question.solution or "")

    # Check if all parts were completed
    all_parts_answered = all(
        QuestionAttempt.objects.filter(
            student=request.user.studentprofile, question_part=p
        ).exists()
        for p in parts
    )

    context = {
        "topic": topic,
        "quickkick": quickkick,
        "view_record": view_record,
        "question": question,
        "parts": parts,
        "student_answers": student_answers,
        "results": results,
        "completed_parts": completed_parts,
        "all_parts_answered": all_parts_answered,
    }

    return render(request, 'quickkicks/quickkick_question.html', context)