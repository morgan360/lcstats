"""Shared plumbing for NumSkull: model choice, conversation memory, safe calls.

Both InfoBot entry points (interactive_lessons.views.info_bot for question
pages, chat.views.chat_view elsewhere) use these so behaviour stays in step.
"""
import logging

from django.conf import settings
from openai import OpenAI

logger = logging.getLogger(__name__)

client = OpenAI()

# Keep the last few exchanges only: enough for "where did the 0.5 come from?"
# to make sense, small enough to stay well inside the session cookie/store.
MAX_TURNS = 3
MAX_STORED_CHARS = 1500

SESSION_KEY = "numskull_history"

FRIENDLY_ERROR = (
    "NumSkull can't think straight right now — the tutor service isn't responding. "
    "Try again in a few minutes, or use the hint and solution buttons in the meantime."
)


def chat_model():
    """The configured chat model (OPENAI_CHAT_MODEL in .env)."""
    return getattr(settings, "OPENAI_CHAT_MODEL", "gpt-4o-mini")


def vision_model():
    """The configured vision model (OPENAI_VISION_MODEL in .env).

    Exam questions carry no text in the prompt - their wording exists only in
    the question image - so image-bearing calls go here rather than to the
    small chat model, which read an already-isolated equation and still
    described the step to isolate it.
    """
    return getattr(settings, "OPENAI_VISION_MODEL", "gpt-4o")


def relevant_context(scored, limit=3):
    """Note contents worth putting in a prompt, best first.

    `scored` is [(similarity, Note)] from search_similar/match_note. Anything
    below RAG_CONTEXT_MIN_SCORE is dropped: a weak match is not background,
    it's a distraction.
    """
    floor = getattr(settings, "RAG_CONTEXT_MIN_SCORE", 0.45)
    return [note.content for score, note in scored[:limit] if score >= floor]


def get_history(request, context_key):
    """Recent (role, content) messages for this question, oldest first.

    History is scoped to context_key — moving to a different question (or a
    different page) starts a fresh conversation rather than dragging the old
    one along.
    """
    stored = request.session.get(SESSION_KEY) or {}
    if stored.get("key") != context_key:
        return []
    return stored.get("messages", [])


def append_turn(request, context_key, question, answer):
    """Record one question/answer exchange against context_key."""
    stored = request.session.get(SESSION_KEY) or {}
    messages = stored.get("messages", []) if stored.get("key") == context_key else []

    messages.append({"role": "user", "content": question[:MAX_STORED_CHARS]})
    messages.append({"role": "assistant", "content": (answer or "")[:MAX_STORED_CHARS]})

    # Trim to the most recent MAX_TURNS exchanges (2 messages per exchange)
    messages = messages[-(MAX_TURNS * 2):]

    request.session[SESSION_KEY] = {"key": context_key, "messages": messages}
    request.session.modified = True


def clear_history(request):
    request.session.pop(SESSION_KEY, None)
    request.session.modified = True


def ask_openai(messages, temperature=0.3, model=None):
    """Call the model, returning (answer, error_message).

    Never raises: a provider outage, an expired key or an exhausted balance
    should show students a friendly note, not a 500 page.
    """
    model = model or chat_model()

    def _create(**extra):
        return client.chat.completions.create(model=model, messages=messages, **extra)

    try:
        try:
            response = _create(temperature=temperature)
        except Exception as exc:
            # Some models accept only the default temperature (gpt-5.5 rejects
            # 0.3, gpt-5.4-mini takes it). Retrying without beats keeping a
            # list of which model is which and getting it wrong later.
            if "temperature" not in str(exc):
                raise
            response = _create()
        return response.choices[0].message.content, None
    except Exception as exc:
        logger.exception("NumSkull chat completion failed: %s", exc)
        return None, FRIENDLY_ERROR
