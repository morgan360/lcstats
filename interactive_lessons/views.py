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

from .models import Topic, Question, QuestionPart
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
    """Answer a student's free-text question using Notes or GPT fallback."""
    query = request.GET.get("query", "").strip()
    if not query:
        return JsonResponse({"answer": ""})

    note, confidence, scored = match_note(query, topic=topic_slug)

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
        )
        return JsonResponse({"answer": html_answer})

    context_text = "\n\n".join([n.content for _, n in scored[:3]])
    prompt = (
        f"You are a Leaving Cert Honours Maths tutor.\n\n"
        f"Relevant notes:\n{context_text}\n\n"
        f"Question:\n{query}"
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
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
    )

    return JsonResponse({"answer": html_answer})


# ----------------------------------------------------------------------
# Topic selection / completion
# ----------------------------------------------------------------------
def select_topic(request):
    topics = Topic.objects.all().order_by("name")
    return render(request, "interactive_lessons/select_topic.html", {"topics": topics})


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
    questions = topic.questions.prefetch_related("parts").order_by("id")
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
View question in admin: {request.build_absolute_uri(f'/admin/interactive_lessons/question/{question.id}/change/')}
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
