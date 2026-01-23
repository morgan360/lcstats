from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q, Count, Sum, Prefetch
from django.views.decorators.http import require_POST
import json
import logging

from .models import (
    ExamPaper, ExamQuestion, ExamQuestionPart,
    ExamAttempt, ExamQuestionAttempt
)
from interactive_lessons.models import Topic
from .services.vision_grading import grade_with_vision_marking_scheme

logger = logging.getLogger(__name__)


@login_required
def paper_list(request):
    """Display list of all available exam papers organized by year"""
    papers = ExamPaper.objects.filter(is_published=True).order_by('-year', 'paper_type')

    # Attach attempt data to each paper
    for paper in papers:
        # Get active (incomplete) attempt for full_timed mode
        paper.active_attempt = ExamAttempt.objects.filter(
            student=request.user,
            exam_paper=paper,
            attempt_mode='full_timed',
            is_completed=False
        ).first()

        # Get best completed attempt
        paper.completed_attempt = ExamAttempt.objects.filter(
            student=request.user,
            exam_paper=paper,
            attempt_mode='full_timed',
            is_completed=True
        ).order_by('-percentage_score').first()

    # Group papers by year
    papers_by_year = {}
    for paper in papers:
        if paper.year not in papers_by_year:
            papers_by_year[paper.year] = []
        papers_by_year[paper.year].append(paper)

    context = {
        'papers_by_year': dict(sorted(papers_by_year.items(), reverse=True)),
    }
    return render(request, 'exam_papers/paper_list.html', context)


@login_required
def paper_detail(request, slug):
    """Display exam paper details with option to start timed or practice mode"""
    paper = get_object_or_404(ExamPaper, slug=slug, is_published=True)

    # Get questions with parts
    questions = paper.questions.prefetch_related('parts', 'topic').order_by('order')

    # Get user's previous attempts
    previous_attempts = ExamAttempt.objects.filter(
        student=request.user,
        exam_paper=paper
    ).order_by('-started_at')

    # Check if user has an active (incomplete) attempt
    active_attempt = previous_attempts.filter(is_completed=False).first()

    context = {
        'paper': paper,
        'questions': questions,
        'previous_attempts': previous_attempts,
        'active_attempt': active_attempt,
    }
    return render(request, 'exam_papers/paper_detail.html', context)


@login_required
@require_POST
def start_paper_attempt(request, slug):
    """Start a new exam attempt (timed or practice mode)"""
    paper = get_object_or_404(ExamPaper, slug=slug, is_published=True)

    # Get mode from POST data
    mode = request.POST.get('mode', 'question_practice')

    # Check if user already has an incomplete attempt for THIS MODE
    active_attempt = ExamAttempt.objects.filter(
        student=request.user,
        exam_paper=paper,
        is_completed=False,
        attempt_mode=mode  # Only resume if same mode
    ).first()

    if active_attempt:
        # Resume existing attempt of the same mode
        attempt = active_attempt
    else:
        # Create new attempt
        attempt = ExamAttempt.objects.create(
            student=request.user,
            exam_paper=paper,
            attempt_mode=mode,
            total_marks_possible=paper.total_marks
        )

    # Redirect to specific question if provided, otherwise first question
    question_id = request.POST.get('question_id')
    if question_id:
        target_question = paper.questions.filter(id=question_id).first()
    else:
        target_question = paper.questions.order_by('order').first()

    if target_question:
        return redirect('exam_papers:question_interface',
                       attempt_id=attempt.id,
                       question_id=target_question.id)
    else:
        return redirect('exam_papers:paper_detail', slug=slug)


@login_required
def question_interface(request, attempt_id, question_id):
    """Display question interface with timer and answer submission"""
    attempt = get_object_or_404(ExamAttempt, id=attempt_id, student=request.user)
    question = get_object_or_404(ExamQuestion, id=question_id, exam_paper=attempt.exam_paper)

    # Get all parts for this question
    parts = question.parts.order_by('order')

    # Get previous attempts for each part
    parts_with_attempts = []
    for part in parts:
        # Get all attempts for this part in this exam attempt
        part_attempts = ExamQuestionAttempt.objects.filter(
            exam_attempt=attempt,
            question_part=part
        ).order_by('-submitted_at')

        # Count attempts
        attempt_count = part_attempts.count()

        # Check if student has a correct answer
        has_correct_answer = part_attempts.filter(is_correct=True).exists()

        # Check if solution is unlocked (unlocks if: correct answer OR reached threshold OR set to 0)
        solution_unlocked = (
            has_correct_answer or
            part.solution_unlock_after_attempts == 0 or
            attempt_count >= part.solution_unlock_after_attempts
        )

        # Get latest attempt
        latest_attempt = part_attempts.first()

        parts_with_attempts.append({
            'part': part,
            'attempts': part_attempts,
            'attempt_count': attempt_count,
            'solution_unlocked': solution_unlocked,
            'latest_attempt': latest_attempt,
        })

    # Calculate time remaining (for timed mode)
    time_remaining = None
    timer_percentage = 0
    if attempt.attempt_mode == 'full_timed':
        elapsed = (timezone.now() - attempt.started_at).total_seconds()
        time_limit = attempt.exam_paper.time_limit_minutes * 60
        time_remaining = int(max(0, time_limit - elapsed))

        # Calculate timer progress percentage
        if time_limit > 0:
            timer_percentage = (time_remaining / time_limit) * 100

        # Auto-submit if time is up
        if time_remaining == 0 and not attempt.is_completed:
            attempt.is_completed = True
            attempt.completed_at = timezone.now()
            attempt.calculate_score()
            return redirect('exam_papers:view_results', attempt_id=attempt.id)

    # Get navigation (previous/next questions)
    all_questions = list(attempt.exam_paper.questions.order_by('order'))
    current_index = next((i for i, q in enumerate(all_questions) if q.id == question.id), 0)

    prev_question = all_questions[current_index - 1] if current_index > 0 else None
    next_question = all_questions[current_index + 1] if current_index < len(all_questions) - 1 else None

    context = {
        'attempt': attempt,
        'question': question,
        'parts_with_attempts': parts_with_attempts,
        'time_remaining': time_remaining,
        'timer_percentage': timer_percentage,
        'prev_question': prev_question,
        'next_question': next_question,
        'is_last_question': next_question is None,
        'question_number': current_index + 1,
        'total_questions': len(all_questions),
    }
    return render(request, 'exam_papers/question_interface.html', context)


@login_required
@require_POST
def submit_answer(request, attempt_id):
    """Submit an answer for a question part"""
    attempt = get_object_or_404(ExamAttempt, id=attempt_id, student=request.user)

    # Check if attempt is still active
    if attempt.is_completed:
        return JsonResponse({
            'success': False,
            'error': 'This attempt has been completed'
        })

    try:
        data = json.loads(request.body)
        part_id = data.get('part_id')
        student_answer = data.get('answer', '').strip()
        time_spent = data.get('time_spent', 0)

        part = get_object_or_404(ExamQuestionPart, id=part_id)

        # Count previous attempts
        previous_attempts = ExamQuestionAttempt.objects.filter(
            exam_attempt=attempt,
            question_part=part
        ).count()

        # Grade the answer using GPT-4 Vision with marking scheme image
        grading_result = grade_with_vision_marking_scheme(
            student_answer=student_answer,
            marking_scheme_image=part.solution_image,
            question_part_label=part.label,
            max_marks=part.max_marks,  # Pass existing max_marks (or None)
            question_image=None,  # No part.image anymore
            hint_used=False,
            solution_used=False
        )

        # Extract results from grading
        marks_awarded = grading_result['marks_awarded']
        is_correct = grading_result['is_correct']
        feedback = grading_result.get('feedback', '')
        extracted_max_marks = grading_result.get('max_marks', part.max_marks)

        # Save extracted max_marks to database if it was auto-extracted
        if part.max_marks is None and extracted_max_marks:
            part.max_marks = extracted_max_marks
            part.save(update_fields=['max_marks'])
            logger.info(f"Saved auto-extracted max_marks={extracted_max_marks} for {part}")

        # Create attempt record
        question_attempt = ExamQuestionAttempt.objects.create(
            exam_attempt=attempt,
            question_part=part,
            student_answer=student_answer,
            marks_awarded=marks_awarded,
            max_marks=part.max_marks,
            is_correct=is_correct,
            feedback=feedback,  # Use enhanced feedback
            attempt_number=previous_attempts + 1,
            time_spent_seconds=time_spent
        )

        # Update exam attempt score
        attempt.calculate_score()

        # Check if solution is now unlocked
        # Solution unlocks if: correct answer OR reached attempt threshold OR set to 0
        total_attempts = previous_attempts + 1
        solution_unlocked = (
            is_correct or  # Unlock immediately if correct
            part.solution_unlock_after_attempts == 0 or
            total_attempts >= part.solution_unlock_after_attempts
        )

        return JsonResponse({
            'success': True,
            'is_correct': is_correct,
            'marks_awarded': marks_awarded,
            'max_marks': part.max_marks,
            'feedback': feedback,  # Return enhanced feedback
            'attempt_number': total_attempts,
            'solution_unlocked': solution_unlocked,
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
def get_solution(request, attempt_id, part_id):
    """Get solution for a question part (if unlocked)"""
    attempt = get_object_or_404(ExamAttempt, id=attempt_id, student=request.user)
    part = get_object_or_404(ExamQuestionPart, id=part_id)

    # Get all attempts for this part
    part_attempts = ExamQuestionAttempt.objects.filter(
        exam_attempt=attempt,
        question_part=part
    )
    attempt_count = part_attempts.count()

    # Check if student has a correct answer
    has_correct_answer = part_attempts.filter(is_correct=True).exists()

    # Check if unlocked (unlocks if: correct answer OR reached threshold OR set to 0)
    solution_unlocked = (
        has_correct_answer or
        part.solution_unlock_after_attempts == 0 or
        attempt_count >= part.solution_unlock_after_attempts
    )

    if not solution_unlocked:
        return JsonResponse({
            'success': False,
            'error': f'Solution unlocks after {part.solution_unlock_after_attempts} attempts. You have made {attempt_count} attempts.',
            'attempts_remaining': part.solution_unlock_after_attempts - attempt_count
        })

    # Mark solution as viewed
    latest_attempt = ExamQuestionAttempt.objects.filter(
        exam_attempt=attempt,
        question_part=part
    ).order_by('-submitted_at').first()

    if latest_attempt:
        latest_attempt.solution_viewed = True
        latest_attempt.save()

    return JsonResponse({
        'success': True,
        'solution_image_url': part.solution_image.url if part.solution_image else None,
    })


@login_required
@require_POST
def complete_attempt(request, attempt_id):
    """Mark an exam attempt as complete"""
    attempt = get_object_or_404(ExamAttempt, id=attempt_id, student=request.user)

    if not attempt.is_completed:
        attempt.is_completed = True
        attempt.is_submitted = True
        attempt.completed_at = timezone.now()
        attempt.time_spent_seconds = int((attempt.completed_at - attempt.started_at).total_seconds())
        attempt.calculate_score()

    return redirect('exam_papers:view_results', attempt_id=attempt.id)


@login_required
def view_results(request, attempt_id):
    """Display results for a completed exam attempt"""
    attempt = get_object_or_404(ExamAttempt, id=attempt_id, student=request.user)

    # Get all question attempts grouped by question
    questions = []
    for exam_question in attempt.exam_paper.questions.order_by('order'):
        parts_data = []
        for part in exam_question.parts.order_by('order'):
            part_attempts = ExamQuestionAttempt.objects.filter(
                exam_attempt=attempt,
                question_part=part
            ).order_by('-submitted_at')

            best_attempt = part_attempts.order_by('-marks_awarded').first()

            parts_data.append({
                'part': part,
                'attempts': part_attempts,
                'best_attempt': best_attempt,
                'total_attempts': part_attempts.count(),
            })

        questions.append({
            'question': exam_question,
            'parts': parts_data,
        })

    context = {
        'attempt': attempt,
        'questions': questions,
    }
    return render(request, 'exam_papers/results.html', context)


@login_required
def topic_practice(request, topic_id):
    """Display exam questions filtered by topic for practice"""
    topic = get_object_or_404(Topic, id=topic_id)

    # Get all published exam questions for this topic
    questions = ExamQuestion.objects.filter(
        topic=topic,
        exam_paper__is_published=True
    ).select_related('exam_paper').prefetch_related('parts').order_by('-exam_paper__year', 'order')

    # Get user's attempts for these questions
    user_attempts = {}
    if request.user.is_authenticated:
        for question in questions:
            for part in question.parts.all():
                attempts = ExamQuestionAttempt.objects.filter(
                    exam_attempt__student=request.user,
                    question_part=part
                )
                user_attempts[part.id] = {
                    'count': attempts.count(),
                    'best_score': attempts.order_by('-marks_awarded').first()
                }

    context = {
        'topic': topic,
        'questions': questions,
        'user_attempts': user_attempts,
    }
    return render(request, 'exam_papers/topic_practice.html', context)


@login_required
@require_POST
def exam_question_feedback(request, attempt_id):
    """Submit feedback (thumbs up/down) for exam question grading/feedback."""
    import json
    from .models import ExamQuestionFeedback, ExamQuestionAttempt

    try:
        data = json.loads(request.body)
        feedback_type = data.get("feedback_type")  # 'helpful' or 'not_helpful'

        if feedback_type not in ['helpful', 'not_helpful']:
            return JsonResponse({"success": False, "error": "Invalid feedback type"}, status=400)

        # Get the attempt and verify it belongs to the current user
        attempt = get_object_or_404(ExamQuestionAttempt, id=attempt_id, exam_attempt__student=request.user)

        # Create or update feedback
        feedback, created = ExamQuestionFeedback.objects.update_or_create(
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
        print(f"[Exam Question Feedback Error] {e}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)