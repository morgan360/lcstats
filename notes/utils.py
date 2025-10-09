import numpy as np
from openai import OpenAI
from django.db.models import Q
from notes.models import Note
from django.conf import settings
from sklearn.metrics.pairwise import cosine_similarity

client = OpenAI(api_key=settings.OPENAI_API_KEY)
EMBED_MODEL = getattr(settings, "OPENAI_EMBED_MODEL", "text-embedding-3-small")


def get_query_embedding(text: str):
    """Create an embedding for the user's question, matching note context."""
    query_text = f"Student question about Leaving Cert Maths:\n{text.strip()}"
    resp = client.embeddings.create(model=EMBED_MODEL, input=query_text)
    return np.array(resp.data[0].embedding, dtype=np.float32)


def search_similar(query, topic=None, top_n=5):
    """
    Retrieve the most relevant notes for a given query.
    Returns a list of (similarity_score, note).
    """
    # --- 1️⃣ Create embedding for the query ---
    query_vec = get_query_embedding(query)

    # --- 2️⃣ Get candidate notes ---
    notes = Note.objects.exclude(embedding__isnull=True)

    if topic:
        topic_normalized = topic.replace("-", " ").lower()
        notes = notes.filter(
            Q(topic__name__icontains=topic_normalized)
            | Q(title__icontains=topic_normalized)
            | Q(topic__name__icontains="statistics")  # fallback for general stats
        ).distinct()

    # --- 3️⃣ Compute cosine similarities ---
    scored = []
    for note in notes:
        try:
            vec = np.array(note.embedding, dtype=np.float32)
            if vec.size == 0 or np.isnan(vec).any():
                continue

            # Handle vector dimension mismatches gracefully
            if vec.size != query_vec.size:
                print(f"⚠️ Skipping {note.title}: dim mismatch {vec.size} vs {query_vec.size}")
                continue

            # Compute cosine similarity via sklearn
            sim = cosine_similarity([query_vec], [vec])[0][0]
            if np.isnan(sim):
                continue

            scored.append((float(sim), note))

        except Exception as e:
            print(f"⚠️ Error computing sim for {note.title}: {e}")
            continue

    # --- 4️⃣ Sort by relevance and apply fallback if needed ---
    scored.sort(reverse=True, key=lambda x: x[0])

    if not scored:
        print("⚠️ No topic match found — falling back to general statistics notes.")
        fallback = Note.objects.filter(topic__icontains="statistics")[:3]
        scored = [(0.0, n) for n in fallback]

    # --- 5️⃣ Debug log ---
    if scored:
        print("🔍 RAG retrieved:")
        for s, n in scored[:top_n]:
            print(f"   {n.title} → {s:.3f}")
    else:
        print("🔍 RAG found no relevant notes.")

    return scored[:top_n]
