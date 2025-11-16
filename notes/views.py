# notes/views.py
from django.shortcuts import render, get_list_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Note
import json

# -------------------------------------------------------------------------
# NOTES INDEX - LIST ALL STUDY RESOURCES
# -------------------------------------------------------------------------
def notes_index(request):
    """Display all available study resources organized by topic."""
    from interactive_lessons.models import Topic

    # Get all topics that have notes
    topics_with_notes = []
    for topic in Topic.objects.all().order_by('name'):
        notes = Note.objects.filter(topic=topic).order_by('-id')
        if notes.exists():
            topics_with_notes.append({
                'topic': topic,
                'notes': notes,
                'count': notes.count()
            })

    return render(request, "notes/notes_index.html", {
        "topics_with_notes": topics_with_notes,
    })

# -------------------------------------------------------------------------
# DISPLAY NOTES BY TOPIC
# -------------------------------------------------------------------------
def notes_topic(request, topic_name):
    """Display all notes for a given topic (by name or ID)."""
    from interactive_lessons.models import Topic
    import markdown
    from markdown_katex import KatexExtension

    # Try to get topic by ID first, then by name/slug
    try:
        topic_id = int(topic_name)
        topic = Topic.objects.get(id=topic_id)
    except (ValueError, Topic.DoesNotExist):
        # Try by slug or name
        try:
            topic = Topic.objects.get(slug=topic_name)
        except Topic.DoesNotExist:
            topic = Topic.objects.get(name=topic_name)

    notes = Note.objects.filter(topic=topic).order_by('-id')

    if not notes.exists():
        # Return 404 if no notes found
        from django.http import Http404
        raise Http404(f"No study resources found for {topic.name}")

    # Render markdown content for each note
    for note in notes:
        if note.content:
            note.content_html = markdown.markdown(
                note.content,
                extensions=["extra", "fenced_code", "tables", KatexExtension()],
            )
        else:
            note.content_html = ""

    return render(request, "notes/topic_notes.html", {
        "topic_name": topic.name,
        "topic": topic,
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
