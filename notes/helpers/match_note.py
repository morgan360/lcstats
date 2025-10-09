import numpy as np
from notes.utils import search_similar
from notes.models import Note
from django.conf import settings

def match_note(query: str, topic: str = None, threshold: float = None, top_n: int = 5):
    """
    Retrieve the most relevant note for a given query.
    Uses FAQ_MATCH_THRESHOLD from settings as default.
    Returns:
        best_note (Note or None),
        best_confidence (float),
        top_matches (list of (confidence, Note))
    """
    # 1️⃣ Pick threshold from settings if not passed in
    threshold = threshold or getattr(settings, "FAQ_MATCH_THRESHOLD", 0.72)

    # 2️⃣ Use your robust search_similar() util
    scored = search_similar(query, topic=topic, top_n=top_n)

    if not scored:
        print("⚠️ No notes retrieved.")
        return None, None, []

    # 3️⃣ Sort again for safety and extract top note
    scored.sort(reverse=True, key=lambda x: x[0])
    best_confidence, best_note = scored[0]

    # 4️⃣ Decide if strong enough for direct answer
    if best_confidence >= threshold:
        print(f"✅ match_note: strong match ({best_confidence:.3f}) → {best_note.title}")
        return best_note, best_confidence, scored
    else:
        print(f"ℹ️ match_note: weak match ({best_confidence:.3f}); will use GPT fallback")
        return None, best_confidence, scored
