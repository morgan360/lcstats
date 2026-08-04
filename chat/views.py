import re

import markdown
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.utils.safestring import mark_safe

from notes.helpers.numskull import append_turn, ask_openai, get_history, relevant_context
from notes.helpers.site_help import match_site_help
from notes.models import InfoBotQuery
from notes.utils import search_similar


def _markdown_to_html(raw_text):
    answer_html = markdown.markdown(
        raw_text,
        extensions=["fenced_code", "tables"],
        output_format="html5",
    )
    # Fix escaped backslashes for MathJax/KaTeX
    return re.sub(r"\\\\", r"\\", answer_html)


@login_required
def chat_view(request):
    """
    NumSkull's fallback endpoint: called by the mascot whenever the current
    page has no [data-numskull-context] (i.e. everywhere outside a practice
    or exam question). Tries to answer "how do I use NumScoil" questions
    from stored site-help notes (pure retrieval, no GPT call); only falls
    back to the general maths-tutor GPT prompt when no site-help note is a
    plausible match at all.
    """
    query = request.GET.get("query")
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    answer = None
    query_id = None
    retrieved_notes = []

    if not query and is_ajax:
        return JsonResponse({"answer": ""})

    if query:
        audience = 'teacher' if request.user.is_staff else 'student'
        site_help_matches = match_site_help(query, audience)
        best_confidence, best_note = site_help_matches[0] if site_help_matches else (None, None)

        if best_note and best_confidence >= settings.SITE_HELP_MIN_CONFIDENCE:
            # Tiers 1 & 2: answer straight from the note, no GPT call.
            answer_html = _markdown_to_html(best_note.content)
            if best_confidence < settings.SITE_HELP_MATCH_THRESHOLD:
                answer_html = (
                    "<p><em>I'm not 100% sure, but this might help:</em></p>" + answer_html
                )
            answer = mark_safe(answer_html)

            log = InfoBotQuery.objects.create(
                question=query,
                answer=answer_html,
                confidence=best_confidence,
                sources=best_note.title,
                source_type='notes',
            )
            query_id = log.id

        else:
            # Tier 3: no usable site-help match — fall back to the existing
            # general maths-tutor behavior, unchanged.
            retrieved = search_similar(query)
            retrieved_notes = relevant_context(retrieved)
            context_text = "\n\n".join(retrieved_notes)

            # The site serves several subjects — don't hand a Physics student
            # a maths tutor.
            current_subject = getattr(request, 'current_subject', None)
            subject_name = current_subject.name if current_subject else "Maths"

            prompt = f"""
            You are NumSkull, a Leaving Cert Honours {subject_name} tutor.
            Explain the following question clearly.
            Use LaTeX for any formulas (use $...$ for inline and $$...$$ for display).

            Question:
            {query}

            Helpful background notes:
            {context_text}
            """

            context_key = f"chat:{subject_name}"
            messages = get_history(request, context_key) + [
                {"role": "user", "content": prompt}
            ]

            raw_answer, error = ask_openai(messages)
            if error:
                answer = mark_safe(f"<p>{error}</p>")
                if is_ajax:
                    return JsonResponse({"answer": answer, "query_id": None})
                return render(request, "chat/chat.html", {"query": query, "answer": answer, "notes": []})

            raw_answer = raw_answer.strip()
            append_turn(request, context_key, query, raw_answer)

            answer_html = _markdown_to_html(raw_answer)
            answer = mark_safe(answer_html)

            log = InfoBotQuery.objects.create(
                question=query,
                answer=answer_html,
                sources=", ".join(note.title for _, note in retrieved),
                source_type='ai',
            )
            query_id = log.id

    if is_ajax:
        return JsonResponse({"answer": answer or "", "query_id": query_id})

    context = {
        "query": query,
        "answer": answer,
        "notes": retrieved_notes,
    }
    return render(request, "chat/chat.html", context)
