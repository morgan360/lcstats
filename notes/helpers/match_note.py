import numpy as np
from notes.utils import search_similar
from notes.models import Note
from django.conf import settings

def expand_query(query: str) -> str:
    """
    Expand short queries with context to improve embedding similarity.
    E.g., 'mean' → 'what is the mean average in statistics how to calculate'
    """
    import re

    # Common expansions for math terms
    expansions = {
        'mean': 'mean average central value sum divided count',
        'median': 'median middle value sorted data',
        'mode': 'mode most frequent common value',
        'standard deviation': 'standard deviation SD spread variance dispersion',
        'variance': 'variance spread squared deviation',
        'range': 'range difference maximum minimum',
        'quartile': 'quartile Q1 Q2 Q3 percentile 25% 75%',
        'correlation': 'correlation relationship association r value',
    }

    # Make query lowercase for matching
    query_lower = query.lower()

    # Check if query contains any key terms
    expanded_terms = []
    for term, expansion in expansions.items():
        if term in query_lower:
            expanded_terms.append(expansion)

    # Combine original query with expansions
    if expanded_terms:
        return f"{query} {' '.join(expanded_terms)}"

    return query

def match_note(query: str, topic: str = None, threshold: float = None, top_n: int = 5, question_context: str = None):
    """
    Retrieve the most relevant note for a given query.
    Uses FAQ_MATCH_THRESHOLD from settings as default.
    Args:
        query: Student's question
        topic: Topic slug to filter notes
        threshold: Confidence threshold for direct answer
        top_n: Number of top matches to return
        question_context: Optional context about the question being worked on
    Returns:
        best_note (Note or None),
        best_confidence (float),
        top_matches (list of (confidence, Note))
    """
    # 1️⃣ Pick threshold from settings if not passed in
    threshold = threshold or getattr(settings, "FAQ_MATCH_THRESHOLD", 0.72)

    # 2️⃣ Expand query for better matching, optionally including question context
    expanded_query = expand_query(query)
    if question_context:
        # Include question context in the search to improve relevance
        expanded_query = f"{expanded_query} {question_context}"
        print(f"🔍 Query with context: '{query}' + context")
    elif expanded_query != query:
        print(f"🔍 Query expanded: '{query}' → '{expanded_query[:80]}...'")

    # 3️⃣ Use your robust search_similar() util with expanded query
    scored = search_similar(expanded_query, topic=topic, top_n=top_n)

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
