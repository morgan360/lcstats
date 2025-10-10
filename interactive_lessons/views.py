from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.utils.safestring import mark_safe
from openai import OpenAI
from notes.utils import search_similar
from notes.models import InfoBotQuery
from django.utils import timezone
import markdown
from markdown_katex import KatexExtension   # ✅ for math rendering
import random
from students.models import QuestionAttempt
from .models import Topic, Question
from .stats_tutor import mark_student_answer
from notes.helpers.match_note import match_note
from django.shortcuts import render, get_object_or_404, redirect
from interactive_lessons.models import Topic, Question  # adjust names to match your models
from django.contrib.auth.decorators import login_required

client = OpenAI()

# -------------------------------------------------------------------------
# INFO BOT – answers questions, uses RAG, logs confidence + source type
# -------------------------------------------------------------------------
def info_bot(request, topic_slug):
    query = request.GET.get("query", "").strip()
    if not query:
        return JsonResponse({"answer": ""})

    # --- Try to match a note directly ---
    note, confidence, scored = match_note(query, topic=topic_slug)

    if note:
        html_answer = markdown.markdown(
            note.content,
            extensions=["extra", "fenced_code", "tables", KatexExtension()]
        )
        InfoBotQuery.objects.create(
            topic_slug=topic_slug,
            question=query,
            answer=note.content,
            confidence=confidence,
            sources=note.title,
            source_type="notes"
        )
        return JsonResponse({"answer": html_answer})

    # --- Otherwise use GPT fallback ---
    context_text = "\n\n".join([n.content for _, n in scored[:3]])
    prompt = f"You are a Leaving Cert Honours Maths tutor.\n\nNotes:\n{context_text}\n\nQuestion:\n{query}"

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    raw_answer = response.choices[0].message.content

    html_answer = markdown.markdown(
        raw_answer,
        extensions=["extra", "fenced_code", "tables", KatexExtension()]
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


# -------------------------------------------------------------------------
# MARKDOWN RENDERING (for skill and question text)
# -------------------------------------------------------------------------
def render_math_markdown(text):
    """Convert Markdown + LaTeX to HTML compatible with KaTeX/MathJax."""
    if not text:
        return ""
    html = markdown.markdown(
        text,
        extensions=["extra", "fenced_code", "tables", KatexExtension()]
    )
    return mark_safe(html)


# -------------------------------------------------------------------------
# TOPIC SELECTOR PAGE
# -------------------------------------------------------------------------
def select_topic(request):
    """Landing page to choose a quiz topic."""
    topics = Topic.objects.all().order_by("name")
    return render(request, "interactive_lessons/select_topic.html", {"topics": topics})


# -------------------------------------------------------------------------
# QUIZ VIEW
# -------------------------------------------------------------------------
def interactive_quiz(request, topic_name, q_index=1):
    topic = get_object_or_404(Topic, name=topic_name)
    questions = list(topic.questions.all().order_by("order"))
    total = len(questions)
    q_index = max(1, min(q_index, total))
    question = questions[q_index - 1]

    result = None
    student_answer = ""

    if request.method == "POST":
        student_answer = request.POST.get("student_answer", "")
        hint_used = request.POST.get("hint_viewed") == "1"
        solution_used = request.POST.get("solution_viewed") == "1"

        result = mark_student_answer(
            question_text=question.text,
            student_answer=student_answer,
            correct_answer=question.answer,
            hint_used=hint_used,
            solution_used=solution_used,
        )

        if "next" in request.POST:
            if q_index < total:
                return redirect("interactive_quiz", topic_name=topic.name, q_index=q_index + 1)
            else:
                return redirect("topic_complete", topic_name=topic.name)

    # ✅ Render all rich text with Markdown + KaTeX
    question.text = render_math_markdown(question.text)
    question.solution = render_math_markdown(getattr(question, "solution", ""))
    question.hint = render_math_markdown(getattr(question, "hint", ""))

    return render(request, "interactive_lessons/quiz.html", {
        "topic": topic,
        "question": question,
        "index": q_index,
        "total": total,
        "result": result,
        "student_answer": student_answer,
    })


# -------------------------------------------------------------------------
# TOPIC COMPLETION PAGE
# -------------------------------------------------------------------------
def topic_complete(request, topic_name):
    return render(request, "interactive_lessons/topic_complete.html", {"topic_name": topic_name})


# -------------------------------------------------------------------------
# QUESTION VIEW – for numbered list navigation
# -------------------------------------------------------------------------
@login_required
def question_view(request, topic_id, number):
    topic = get_object_or_404(Topic, id=topic_id)
    questions = topic.questions.all().order_by("id")
    total = questions.count()

    if number < 1 or number > total:
        return redirect("question_view", topic_id=topic.id, number=1)

    question = questions[number - 1]
    student_answer = ""
    result = None

    # ✅ Handle "Check Answer" submission
    if request.method == "POST":
        student_answer = request.POST.get("student_answer", "")
        hint_used = request.POST.get("hint_viewed") == "1"
        solution_used = request.POST.get("solution_viewed") == "1"

        # Skip marking if it's the Next button
        if "next" not in request.POST:
            result = mark_student_answer(
                question_text=question.text,
                student_answer=student_answer,
                correct_answer=question.answer,
                hint_used=hint_used,
                solution_used=solution_used,
            )

            # ✅ Record progress attempt
            try:
                QuestionAttempt.objects.create(
                    student=request.user.studentprofile,
                    question=question,
                    student_answer=student_answer,
                    score_awarded=result.get("score", 0),
                    is_correct=result.get("is_correct", False),
                )
            except Exception as e:
                print(f"[Progress Tracking Error] {e}")

        # ✅ Handle "Next →" button
        if "next" in request.POST:
            if number < total:
                return redirect("question_view", topic_id=topic.id, number=number + 1)
            else:
                return redirect("topic_complete", topic_name=topic.name)

    # ✅ Render Markdown + LaTeX before sending to template
    question.text = render_math_markdown(question.text)
    question.hint = render_math_markdown(getattr(question, "hint", ""))
    question.solution = render_math_markdown(getattr(question, "solution", ""))

    context = {
        "topic": topic,
        "question": question,
        "index": number,
        "total": total,
        "questions": questions,
        "student_answer": student_answer,
        "result": result,
    }

    return render(request, "interactive_lessons/quiz.html", context)