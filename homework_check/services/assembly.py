"""Turning several chunk results into one report.

Pure functions: no database, no network, no API key. That is deliberate, so
the rules that decide what a student is told can be tested exhaustively
without mocking anything -- the same reasoning as
``exam_papers/tests/test_work_analysis_mark.py``.
"""
import logging

from .check_analysis import RATING_BANDS, VERDICT_CREDIT, VERDICTS

logger = logging.getLogger(__name__)

# Below this, a rating computed from one or two questions says more about the
# photos than about the student.
MIN_QUESTIONS_FOR_RATING = 2

# Ordered worst to best. When the same question turns up in two chunks and
# both have something to say, the less flattering verdict wins -- an error
# seen on the second page is still an error.
_VERDICT_SEVERITY = {
    "correct": 0,
    "slip": 1,
    "incomplete": 2,
    "wrong": 3,
    "unclear": 4,
}


def _sort_key(label):
    """Order labels the way a copy runs: 2 before 10, 3(a) before 3(b)."""
    lead = ""
    rest = label
    for i, ch in enumerate(label):
        if ch.isdigit():
            lead += ch
            rest = label[i + 1:]
        elif lead:
            rest = label[i:]
            break
    return (int(lead) if lead else 9999, rest.lower(), label.lower())


def merge_questions(chunks):
    """Collapse per-chunk question rows into one row per question label.

    Working that ran across a page break shows up in two chunks under the same
    label. Comments are joined, and the fuller answer wins: a chunk that saw
    the student reach a final answer knows more than one that saw the setup.
    """
    merged = {}

    for chunk in chunks:
        for row in chunk.get("questions") or []:
            label = row["label"]
            if label not in merged:
                merged[label] = dict(row)
                continue

            existing = merged[label]

            # Prefer whichever chunk actually saw a final answer.
            if not existing["student_answer"] and row["student_answer"]:
                existing["student_answer"] = row["student_answer"]
            if not existing["correct_answer"] and row["correct_answer"]:
                existing["correct_answer"] = row["correct_answer"]
                existing["found_in_solutions"] = row["found_in_solutions"]

            if row["comment"] and row["comment"] not in existing["comment"]:
                existing["comment"] = " ".join(
                    p for p in (existing["comment"], row["comment"]) if p
                )

            if _VERDICT_SEVERITY.get(row["verdict"], 4) > \
                    _VERDICT_SEVERITY.get(existing["verdict"], 4):
                existing["verdict"] = row["verdict"]

            existing["continues"] = False

    return sorted(merged.values(), key=lambda r: _sort_key(r["label"]))


def derive_rating(questions, chunks, failed_photos=0):
    """Decide Excellent / Good / Fair / Poor in code, not on the model's word.

    A rating is the one output on this sheet a student will take literally, so
    none of it is left to the model honouring an instruction -- the same
    principle as ``work_analysis._sanitise_mark``. Anything doubtful becomes no
    rating at all, and the teacher sets one by hand.

    Returns (rating, reason). ``rating`` is "" when it is withheld, and
    ``reason`` says why, for the teacher.

    ``failed_photos`` counts pages that never produced a chunk at all. The
    readable/confidence guards below can only inspect chunks that exist, so a
    batch that died mid-run was invisible here: the report was assembled from
    the batches that happened to work and rated as though the whole copy had
    been read. That is a rating on half a student's homework, printed and
    handed to them, with nothing on the sheet saying so.
    """
    if failed_photos:
        return "", (
            f"{failed_photos} page(s) could not be analysed, so this covers "
            "only part of the work"
        )

    for chunk in chunks:
        if not chunk.get("readable", True):
            return "", "some of the photos could not be read clearly"
        if str(chunk.get("confidence") or "").lower() == "low":
            return "", "the model was not confident it read the pages correctly"

    judged = [q for q in questions if q["verdict"] != "unclear"]
    if len(judged) < MIN_QUESTIONS_FOR_RATING:
        return "", (
            "too few questions could be matched to the solutions to rate the "
            "work fairly"
        )

    share = sum(VERDICT_CREDIT.get(q["verdict"], 0.0) for q in judged) / len(judged)
    for threshold, rating in RATING_BANDS:
        if share >= threshold:
            return rating, ""
    return "poor", ""


def tally(questions):
    """Counts per verdict, plus the ones missing from the solutions."""
    counts = {v: 0 for v in VERDICTS}
    for q in questions:
        counts[q["verdict"]] = counts.get(q["verdict"], 0) + 1
    counts["total"] = len(questions)
    counts["not_in_solutions"] = sum(
        1 for q in questions if not q["found_in_solutions"]
    )
    return counts


def fallback_summary(questions, counts):
    """A summary composed in code, for when the summarising call fails.

    Plain counting only. It never says anything the per-question rows do not
    already show, which is what makes it safe to print unreviewed.
    """
    if not questions:
        return "No questions could be read from these photos."

    judged = counts["total"] - counts["unclear"]
    if not judged:
        return (
            f"{counts['total']} question(s) were found, but none could be "
            "matched to the solutions supplied."
        )

    right = counts["correct"]
    bits = [f"{right} of {judged} question(s) fully correct."]
    if counts["slip"]:
        bits.append(
            f"{counts['slip']} had the right method with an arithmetic or "
            "sign slip."
        )
    if counts["wrong"]:
        bits.append(f"{counts['wrong']} used the wrong approach.")
    if counts["incomplete"]:
        bits.append(f"{counts['incomplete']} were left unfinished.")
    return " ".join(bits)


def collect_notes(chunks):
    """The teacher-facing notes from every chunk, deduped and in order."""
    seen = []
    for chunk in chunks:
        note = str(chunk.get("notes") or "").strip()
        if note and note not in seen:
            seen.append(note)
    return seen


def assemble(chunks, failed_photos=0):
    """Build the whole report from the per-chunk results."""
    questions = merge_questions(chunks)
    counts = tally(questions)
    rating, rating_reason = derive_rating(questions, chunks, failed_photos)

    diagram_feedback = " ".join(
        str(c.get("diagram_feedback") or "").strip()
        for c in chunks
        if c.get("has_diagram") and str(c.get("diagram_feedback") or "").strip()
    ).strip()

    return {
        "questions": questions,
        "counts": counts,
        "rating": rating,
        "rating_reason": rating_reason,
        "has_diagram": any(c.get("has_diagram") for c in chunks),
        "diagram_feedback": diagram_feedback,
        "readable": all(c.get("readable", True) for c in chunks),
        "confidence": _lowest_confidence(chunks),
        "notes": collect_notes(chunks),
    }


def _lowest_confidence(chunks):
    order = ["low", "medium", "high"]
    found = [
        str(c.get("confidence") or "").lower() for c in chunks
        if str(c.get("confidence") or "").lower() in order
    ]
    if not found:
        return ""
    return min(found, key=order.index)
