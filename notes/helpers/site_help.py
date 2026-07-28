from notes.utils import search_similar


def match_site_help(query: str, audience: str, top_n: int = 3):
    """
    Retrieve the top site-help note matches for a query, scoped to the given
    audience ('student' or 'teacher'; 'all'-audience notes always match).

    Pure retrieval — no GPT call — so answering from stored notes costs
    nothing beyond the one-time embedding of each note. Returns a list of
    (similarity_score, note), best first, or [] if no site-help notes exist
    for this audience at all.
    """
    return search_similar(query, top_n=top_n, content_type='site_help', audience=audience)
