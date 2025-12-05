from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.utils.safestring import mark_safe
from django.http import JsonResponse
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
import markdown
from markdown_katex import KatexExtension
from openai import OpenAI

from .models import Topic, Question, QuestionPart, StudentInquiry
from students.models import QuestionAttempt
from interactive_lessons.services.marking import grade_submission
from notes.models import InfoBotQuery
from notes.helpers.match_note import match_note
from .forms import QuestionContactForm

client = OpenAI()


# ----------------------------------------------------------------------
# InfoBot (Notes / GPT QA)
# ----------------------------------------------------------------------
def info_bot(request, topic_slug):
    """Answer a student's free-text question using Notes or GPT fallback with question context."""
    query = request.GET.get("query", "").strip()
    if not query:
        return JsonResponse({"answer": ""})

    # Extract optional question context parameters
    practice_question_id = request.GET.get("practice_question_id")
    exam_question_id = request.GET.get("exam_question_id")
    question_part_id = request.GET.get("question_part_id")

    # Build question context string and collect image URLs
    question_context_str = ""
    question_context_parts = []
    question_image_urls = []  # Collect image URLs for vision

    if practice_question_id:
        try:
            from .models import QuestionPart
            practice_q = Question.objects.get(id=practice_question_id)
            question_context_parts.append(f"Topic: {practice_q.topic.name}")
            if practice_q.hint:
                question_context_parts.append(f"Question hint: {practice_q.hint[:200]}")

            # Collect question image if available
            question_image = practice_q.get_image()  # Using get_image() method
            if question_image:
                question_context_parts.append(f"This question includes a diagram (see image)")
                image_url = request.build_absolute_uri(question_image)
                question_image_urls.append({"url": image_url, "description": "Practice question diagram"})

            # If specific part is mentioned, include it
            if question_part_id:
                try:
                    part = QuestionPart.objects.get(id=question_part_id)
                    question_context_parts.append(f"Question part ({part.label}): {part.prompt[:300]}")
                    # Collect part image if available
                    if part.image:
                        question_context_parts.append(f"Part {part.label} includes a diagram (see image)")
                        part_image_url = request.build_absolute_uri(part.image.url)
                        question_image_urls.append({"url": part_image_url, "description": f"Part {part.label} diagram"})
                except QuestionPart.DoesNotExist:
                    pass
        except Question.DoesNotExist:
            pass

    elif exam_question_id:
        try:
            from exam_papers.models import ExamQuestion, ExamQuestionPart
            exam_q = ExamQuestion.objects.get(id=exam_question_id)

            # Add exam paper context
            question_context_parts.append(f"Exam Paper: {exam_q.exam_paper.year} {exam_q.exam_paper.get_paper_type_display()}")
            question_context_parts.append(f"Question {exam_q.question_number}")

            if exam_q.title:
                question_context_parts.append(f"Question Title: {exam_q.title}")

            if exam_q.topic:
                question_context_parts.append(f"Topic: {exam_q.topic.name}")

            # Collect question image if available
            if exam_q.image:
                question_context_parts.append(f"This question includes a diagram (see image)")
                # Build absolute URL for the image
                image_url = request.build_absolute_uri(exam_q.image.url)
                question_image_urls.append({"url": image_url, "description": f"Question {exam_q.question_number} diagram"})

            # If specific part is mentioned, include it
            if question_part_id:
                try:
                    part = ExamQuestionPart.objects.get(id=question_part_id)
                    question_context_parts.append(f"Question part {part.label}")
                    # Collect part image if available
                    if part.image:
                        question_context_parts.append(f"Part {part.label} includes a diagram (see image)")
                        part_image_url = request.build_absolute_uri(part.image.url)
                        question_image_urls.append({"url": part_image_url, "description": f"Part {part.label} diagram"})
                except ExamQuestionPart.DoesNotExist:
                    pass
        except:
            pass

    question_context_str = "\n".join(question_context_parts)

    # Try matching notes with original query
    note, confidence, scored = match_note(query, topic=topic_slug, question_context=question_context_str)

    if note:
        html_answer = markdown.markdown(
            note.content,
            extensions=["extra", "fenced_code", "tables", KatexExtension()],
        )
        InfoBotQuery.objects.create(
            topic_slug=topic_slug,
            question=query,
            answer=note.content,
            confidence=confidence,
            sources=note.title,
            source_type="notes",
            practice_question_id=int(practice_question_id) if practice_question_id else None,
            exam_question_id=int(exam_question_id) if exam_question_id else None,
            question_part_id=int(question_part_id) if question_part_id else None,
            question_context=question_context_str,
        )
        return JsonResponse({"answer": html_answer})

    # Build enhanced prompt with question context
    context_text = "\n\n".join([n.content for _, n in scored[:3]])

    prompt_parts = [
        "You are NumSkull, a Leaving Cert Honours Maths tutor.",
        "",
        "IMPORTANT INSTRUCTIONS:",
        "- Answer ONLY what the student asks - do not solve their problem for them",
        "- Keep answers brief and focused (2-3 sentences max unless asked to explain)",
        "- DO NOT provide step-by-step solutions unless explicitly asked",
        "- DO NOT work through examples unless asked",
        "- Use LaTeX math notation with $ for inline math and $$ for display math",
        "- Be concise and helpful, but don't do their homework"
    ]

    if question_context_str:
        prompt_parts.append(f"\nStudent is working on:\n{question_context_str}")

    if context_text:
        prompt_parts.append(f"\nRelevant course notes:\n{context_text}")

    prompt_parts.append(f"\nStudent's question:\n{query}")
    prompt_parts.append("\nProvide a brief, direct answer (2-3 sentences). Do not solve the problem or provide step-by-step solutions unless specifically asked.")

    prompt = "\n".join(prompt_parts)

    # Build message with vision support if images are available
    if question_image_urls:
        # Create a multimodal message with text and images
        message_content = [{"type": "text", "text": prompt}]

        # Add each image to the message
        for img_data in question_image_urls:
            message_content.append({
                "type": "image_url",
                "image_url": {
                    "url": img_data["url"],
                    "detail": "low"  # Use low detail to reduce costs (still effective for most diagrams)
                }
            })

        messages = [{"role": "user", "content": message_content}]
    else:
        # Text-only message
        messages = [{"role": "user", "content": prompt}]

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.3,
    )
    raw_answer = response.choices[0].message.content

    html_answer = markdown.markdown(
        raw_answer,
        extensions=["extra", "fenced_code", "tables", KatexExtension()],
    )

    InfoBotQuery.objects.create(
        topic_slug=topic_slug,
        question=query,
        answer=raw_answer,
        confidence=confidence,
        sources=", ".join([n.title for _, n in scored]),
        source_type="ai",
        practice_question_id=int(practice_question_id) if practice_question_id else None,
        exam_question_id=int(exam_question_id) if exam_question_id else None,
        question_part_id=int(question_part_id) if question_part_id else None,
        question_context=question_context_str,
    )

    return JsonResponse({"answer": html_answer})


# ----------------------------------------------------------------------
# Topic selection / completion
# ----------------------------------------------------------------------
def select_topic(request):
    from notes.models import Note
    from revision.models import RevisionModule
    from cheatsheets.models import CheatSheet
    from exam_papers.models import ExamQuestion
    from quickkicks.models import QuickKick
    topics = Topic.objects.all().order_by("name")
    # Annotate topics with note counts, question counts, cheat sheet counts, and revision module info
    topics_with_notes = []
    for topic in topics:
        note_count = Note.objects.filter(topic=topic).count()
        question_count = Question.objects.filter(topic=topic).count()
        cheatsheet_count = CheatSheet.objects.filter(topic=topic).count()
        quickkick_count = QuickKick.objects.filter(topic=topic).count()
        # Count exam questions for this topic (only from published papers)
        exam_question_count = ExamQuestion.objects.filter(
            topic=topic,
            exam_paper__is_published=True
        ).count()
        # Check if this topic has a published revision module
        revision_module = RevisionModule.objects.filter(
            topic=topic,
            is_published=True
        ).first()
        topics_with_notes.append({
            'topic': topic,
            'has_notes': note_count > 0,
            'note_count': note_count,
            'question_count': question_count,
            'cheatsheet_count': cheatsheet_count,
            'has_cheatsheets': cheatsheet_count > 0,
            'quickkick_count': quickkick_count,
            'has_quickkicks': quickkick_count > 0,
            'exam_question_count': exam_question_count,
            'has_exam_questions': exam_question_count > 0,
            'has_revision': revision_module is not None,
            'revision_module': revision_module
        })
    return render(request, "interactive_lessons/select_topic.html", {
        "topics": topics,
        "topics_with_notes": topics_with_notes
    })


@login_required
def section_list(request, topic_slug):
    """Display all sections within a topic with completion status"""
    from interactive_lessons.models import Section
    from students.models import QuestionAttempt

    topic = get_object_or_404(Topic, slug=topic_slug)
    sections = Section.objects.filter(topic=topic).prefetch_related('questions')

    # Calculate completion status for each section
    section_data = []
    for section in sections:
        questions = section.questions.all()
        total_questions = questions.count()

        if total_questions > 0:
            # Count how many questions have been attempted by this student
            attempted_question_ids = QuestionAttempt.objects.filter(
                student=request.user.studentprofile,
                question__in=questions
            ).values_list('question_id', flat=True).distinct()

            completed_questions = len(attempted_question_ids)
            completion_percentage = int((completed_questions / total_questions) * 100)
        else:
            completed_questions = 0
            completion_percentage = 0

        section_data.append({
            'section': section,
            'total_questions': total_questions,
            'completed_questions': completed_questions,
            'completion_percentage': completion_percentage,
            'is_completed': completion_percentage == 100
        })

    context = {
        'topic': topic,
        'section_data': section_data,
    }

    return render(request, 'interactive_lessons/section_list.html', context)


@login_required
def section_quiz(request, topic_slug, section_slug):
    """Start quiz for a specific section"""
    from interactive_lessons.models import Section

    topic = get_object_or_404(Topic, slug=topic_slug)
    section = get_object_or_404(Section, slug=section_slug, topic=topic)

    # Get the first question in this section
    first_question = section.questions.order_by('order').first()

    if first_question:
        return redirect('section_question_view',
                       topic_slug=topic_slug,
                       section_slug=section_slug,
                       number=1)
    else:
        messages.warning(request, f"No questions available in {section.name}")
        return redirect('section_list', topic_slug=topic_slug)


@login_required
def section_question_view(request, topic_slug, section_slug, number):
    """
    Question view filtered to a specific section.
    Similar to question_view but only shows questions from the selected section.
    """
    from interactive_lessons.models import Section

    topic = get_object_or_404(Topic, slug=topic_slug)
    section = get_object_or_404(Section, slug=section_slug, topic=topic)
    questions = section.questions.prefetch_related("parts").order_by("order")
    total = questions.count()

    # --- Bounds check ---
    if number < 1 or number > total:
        return redirect("section_question_view",
                       topic_slug=topic_slug,
                       section_slug=section_slug,
                       number=1)

    question = questions[number - 1]
    parts = question.parts.all().order_by("order")

    results = {}
    student_answers = {}
    completed_parts = set()

    # ------------------------------------------------------------------
    #  POST: grade a single QuestionPart (AJAX submission)
    # ------------------------------------------------------------------
    if request.method == "POST":
        part_id = request.POST.get("part_id")
        if part_id:
            part = get_object_or_404(QuestionPart, id=part_id)
            answer = request.POST.get(f"answer_{part.id}", "").strip()
            student_answers[part.id] = answer

            if answer:
                # --- Grade the submission ---
                result = grade_submission(
                    question_part_id=part.id,
                    student_answer=answer,
                    hint_used=False,
                    solution_used=False,
                ) or {}

                results[part.id] = result
                completed_parts.add(part.id)

                # --- Save attempt for progress tracking ---
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

                # --- AJAX JSON feedback response ---
                if request.headers.get("x-requested-with") == "XMLHttpRequest":
                    return JsonResponse({
                        "is_correct": result.get("is_correct", False),
                        "score": result.get("score", 0),
                        "feedback": result.get("feedback", "No feedback generated."),
                    })

        # --- Handle "Next" button ---
        if "next" in request.POST:
            if number < total:
                return redirect("section_question_view",
                               topic_slug=topic_slug,
                               section_slug=section_slug,
                               number=number + 1)
            else:
                # Section complete, redirect back to section list
                messages.success(request, f"Section '{section.name}' completed!")
                return redirect("section_list", topic_slug=topic_slug)

    # ------------------------------------------------------------------
    #  GET or full-page render
    # ------------------------------------------------------------------
    # Render question and part content (Math/KaTeX compatible)
    question.hint = render_math_markdown(question.hint)
    for part in parts:
        part.prompt = render_math_markdown(part.prompt)
        part.expected_format = render_math_markdown(part.expected_format or "")
        part.solution = render_math_markdown(part.solution or "")

    question.solution = render_math_markdown(question.solution or "")

    # Optional: check if all parts were completed
    all_parts_answered = all(
        QuestionAttempt.objects.filter(
            student=request.user.studentprofile, question_part=p
        ).exists()
        for p in parts
    )

    context = {
        "topic": topic,
        "section": section,
        "question": question,
        "parts": parts,
        "index": number,
        "total": total,
        "questions": questions,
        "student_answers": student_answers,
        "results": results,
        "completed_parts": completed_parts,
        "all_parts_answered": all_parts_answered,
    }

    return render(request, "interactive_lessons/quiz.html", context)


@login_required
def topic_quiz(request, topic_slug):
    """Redirect to section selection for the topic"""
    return redirect('section_list', topic_slug=topic_slug)


def topic_complete(request, topic_name):
    return render(request, "interactive_lessons/topic_complete.html", {"topic_name": topic_name})


# ----------------------------------------------------------------------
# Utility: render markdown with KaTeX
# ----------------------------------------------------------------------
def render_math_markdown(text):
    if not text:
        return ""
    html = markdown.markdown(
        text,
        extensions=["extra", "fenced_code", "tables", KatexExtension()],
    )
    return mark_safe(html)


# ----------------------------------------------------------------------
# Main question view (AJAX + normal render)
# ----------------------------------------------------------------------
@login_required
def question_view(request, topic_id, number):
    topic = get_object_or_404(Topic, id=topic_id)
    questions = topic.questions.prefetch_related("parts").order_by("order")
    total = questions.count()

    # --- Bounds check ---
    if number < 1 or number > total:
        return redirect("question_view", topic_id=topic.id, number=1)

    question = questions[number - 1]
    parts = question.parts.all().order_by("order")

    results = {}
    student_answers = {}
    completed_parts = set()

    # ------------------------------------------------------------------
    #  POST: grade a single QuestionPart (AJAX submission)
    # ------------------------------------------------------------------
    if request.method == "POST":
        part_id = request.POST.get("part_id")
        if part_id:
            part = get_object_or_404(QuestionPart, id=part_id)
            answer = request.POST.get(f"answer_{part.id}", "").strip()
            student_answers[part.id] = answer

            if answer:
                # --- Grade the submission ---
                result = grade_submission(
                    question_part_id=part.id,
                    student_answer=answer,
                    hint_used=False,
                    solution_used=False,
                ) or {}

                results[part.id] = result
                completed_parts.add(part.id)

                # --- Save attempt for progress tracking ---
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

                # --- AJAX JSON feedback response ---
                if request.headers.get("x-requested-with") == "XMLHttpRequest":
                    return JsonResponse({
                        "is_correct": result.get("is_correct", False),
                        "score": result.get("score", 0),
                        "feedback": result.get("feedback", "No feedback generated."),
                    })

        # --- Handle "Next" button ---
        if "next" in request.POST:
            if number < total:
                return redirect("question_view", topic_id=topic.id, number=number + 1)
            else:
                return redirect("topic_complete", topic_name=topic.name)

    # ------------------------------------------------------------------
    #  GET or full-page render
    # ------------------------------------------------------------------
    # Render question and part content (Math/KaTeX compatible)
    question.hint = render_math_markdown(question.hint)
    for part in parts:
        part.prompt = render_math_markdown(part.prompt)
        part.expected_format = render_math_markdown(part.expected_format or "")
        part.solution = render_math_markdown(part.solution or "")

    # ✅ Render the full-question solution text (if any)
    question.solution = render_math_markdown(question.solution or "")

    # Optional: check if all parts were completed
    all_parts_answered = all(
        QuestionAttempt.objects.filter(
            student=request.user.studentprofile, question_part=p
        ).exists()
        for p in parts
    )

    context = {
        "topic": topic,
        "question": question,
        "parts": parts,
        "index": number,
        "total": total,
        "questions": questions,
        "student_answers": student_answers,
        "results": results,
        "completed_parts": completed_parts,
        # ✅ Include this flag if you only want to show the solution after completion
        "all_parts_answered": all_parts_answered,
    }

    return render(request, "interactive_lessons/quiz.html", context)

# ----------------------------------------------------------------------
# Contact teacher about a question
# ----------------------------------------------------------------------
@login_required
def topic_exam_questions(request, topic_slug):
    """Display exam questions for a topic, grouped by year, with student progress"""
    from exam_papers.models import ExamQuestion, ExamQuestionAttempt, ExamAttempt

    topic = get_object_or_404(Topic, slug=topic_slug)

    # Get all published exam questions for this topic, ordered by year (most recent first)
    exam_questions = ExamQuestion.objects.filter(
        topic=topic,
        exam_paper__is_published=True
    ).select_related('exam_paper').prefetch_related('parts').order_by('-exam_paper__year', 'exam_paper__paper_type', 'question_number')

    # Get student's attempts for these questions
    user_attempts = {}
    for question in exam_questions:
        # Get all attempts for parts of this question by this student
        part_attempts = ExamQuestionAttempt.objects.filter(
            exam_attempt__student=request.user,
            question_part__question=question
        ).select_related('question_part')

        if part_attempts.exists():
            # Calculate total marks for this question
            total_marks_awarded = 0
            total_marks_possible = 0
            parts_attempted = set()

            for attempt in part_attempts:
                parts_attempted.add(attempt.question_part.id)
                # Get best attempt for each part
                best_for_part = ExamQuestionAttempt.objects.filter(
                    exam_attempt__student=request.user,
                    question_part=attempt.question_part
                ).order_by('-marks_awarded').first()

                if best_for_part:
                    total_marks_awarded += best_for_part.marks_awarded
                    total_marks_possible += best_for_part.max_marks

            user_attempts[question.id] = {
                'attempted': True,
                'parts_attempted': len(parts_attempted),
                'total_parts': question.parts.count(),
                'marks_awarded': total_marks_awarded,
                'marks_possible': total_marks_possible,
                'percentage': (total_marks_awarded / total_marks_possible * 100) if total_marks_possible > 0 else 0
            }
        else:
            user_attempts[question.id] = {
                'attempted': False,
                'parts_attempted': 0,
                'total_parts': question.parts.count()
            }

    # Group questions by year and paper, and attach attempt data to each question
    questions_by_paper = {}
    for question in exam_questions:
        paper_key = f"{question.exam_paper.year} {question.exam_paper.get_paper_type_display()}"
        if paper_key not in questions_by_paper:
            questions_by_paper[paper_key] = {
                'paper': question.exam_paper,
                'questions': []
            }
        # Attach attempt data directly to question object for easy template access
        question.attempt_data = user_attempts.get(question.id, {
            'attempted': False,
            'parts_attempted': 0,
            'total_parts': question.parts.count()
        })
        questions_by_paper[paper_key]['questions'].append(question)

    context = {
        'topic': topic,
        'questions_by_paper': questions_by_paper,
        'total_questions': exam_questions.count(),
        'user_attempts': user_attempts
    }

    return render(request, 'interactive_lessons/topic_exam_questions.html', context)


@login_required
def question_contact(request, question_id):
    """Allow students to email the teacher about a specific question"""
    question = get_object_or_404(Question, id=question_id)
    
    if request.method == "POST":
        form = QuestionContactForm(
            request.POST,
            question=question,
            student=request.user
        )
        
        if form.is_valid():
            subject = form.cleaned_data['subject']
            message = form.cleaned_data['message']

            # Save inquiry to database
            inquiry = StudentInquiry.objects.create(
                student=request.user,
                question=question,
                subject=subject,
                message=message,
                topic_name=question.topic.name,
                question_number=f"Q{question.order}",
                section_name=question.section if question.section else None,
            )

            # Build email content
            email_body = f"""
Student Question/Inquiry

From: {request.user.get_full_name() or request.user.username} ({request.user.email})

Question Details:
- Topic: {question.topic.name}
- Question: Q{question.order}
{f'- Section: {question.section}' if question.section else ''}

Subject: {subject}

Message:
{message}

---
View and reply in admin: {request.build_absolute_uri(f'/admin/interactive_lessons/studentinquiry/{inquiry.id}/change/')}
            """

            try:
                send_mail(
                    subject=f"[LCAI Maths] Student Question: {subject}",
                    message=email_body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[settings.TEACHER_EMAIL],
                    fail_silently=False,
                )

                messages.success(request, "Your message has been sent! I'll get back to you soon.")
                return redirect('question_view', topic_id=question.topic.id, number=question.order)

            except Exception as e:
                messages.error(request, f"Sorry, there was an error sending your message. Please try again or email directly.")
                print(f"[Email Error] {e}")
    
    else:
        form = QuestionContactForm(question=question, student=request.user)
    
    context = {
        'form': form,
        'question': question,
    }
    
    return render(request, 'interactive_lessons/question_contact.html', context)
