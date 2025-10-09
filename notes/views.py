# notes/views.py
from django.shortcuts import render, get_list_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Note
import json

# -------------------------------------------------------------------------
# DISPLAY NOTES BY TOPIC
# -------------------------------------------------------------------------
def notes_topic(request, topic_name):
    """Display all notes for a given topic."""
    notes = get_list_or_404(Note, topic=topic_name)
    return render(request, "notes/topic_notes.html", {
        "topic_name": topic_name,
        "notes": notes
    })


# -------------------------------------------------------------------------
# SAVE INFO BOT ANSWERS AS PERMANENT NOTES
# -------------------------------------------------------------------------
@csrf_exempt
def save_info(request):
    """Save Info Bot responses as permanent notes."""
    if request.method != "POST":
        return JsonResponse({"message": "Invalid request"}, status=405)

    try:
        data = json.loads(request.body or "{}")
        title = (data.get("title") or "Untitled").strip()
        content = data.get("content") or ""
        topic_slug = (data.get("topic") or "").strip()

        # Build Note fields
        note_fields = {f.name for f in Note._meta.get_fields()}
        create_kwargs = {
            "title": f"AI: {title[:100]}",
            "content": content,
        }

        # If the Note model includes topic and metadata fields, fill them in
        if "topic" in note_fields:
            create_kwargs["topic"] = topic_slug or "general"

        if "metadata" in note_fields:
            # Use the Info Bot's question or title as metadata for embedding context
            create_kwargs["metadata"] = title

        # The Note model's save() will handle embedding automatically
        note = Note.objects.create(**create_kwargs)

        return JsonResponse({"message": "Saved to Notes ✅", "id": note.pk})

    except Exception as e:
        return JsonResponse({"message": f"Error saving note: {e}"}, status=500)
