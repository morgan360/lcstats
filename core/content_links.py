"""Naming and linking the units of content a student can be sent to work on.

Homework tasks and study plan items both point at one of six things -- a topic
section, a whole exam question, a single exam question part, a QuickFlick, a
flashcard set, or a written exercise with no content behind it at all. Each
needs a label a teacher would recognise, a URL that drops the student straight
into the work, and a rule saying which foreign key must be set.

That logic lived only on ``homework.HomeworkTask``. It is here so the study plan
can reuse it rather than grow a second copy that drifts. The *columns* are still
declared on each model: an abstract base would force HomeworkTask's
``task_type`` field and its ``homework_tasks`` related names to change, and
``reports.services`` and the ``merge_question_parts`` command both rely on those.

Every URL carries ``?subject=`` because ``core.middleware.SubjectMiddleware``
reads it to switch the session's subject -- without it a student working on
Physics who opens a Maths task lands in the wrong context.
"""
from django.urls import reverse

#: The six kinds, in the order a teacher meets them. Shared verbatim with
#: ``homework.HomeworkTask.TASK_TYPE_CHOICES``.
CONTENT_KIND_CHOICES = [
    ('section', 'Topic Section'),
    ('exam_question', 'Exam Question'),
    ('exam_part', 'Exam Question Part'),
    ('quickkick', 'QuickFlicks Video/Applet'),
    ('flashcard', 'Flashcard Set'),
    ('custom', 'Written Exercise'),
]

CONTENT_KINDS = [kind for kind, _label in CONTENT_KIND_CHOICES]

#: kind -> the model field holding its foreign key.
CONTENT_FK_FIELDS = {
    'section': 'section',
    'exam_question': 'exam_question',
    'exam_part': 'exam_question_part',
    'quickkick': 'quickkick',
    'flashcard': 'flashcard_set',
}

#: The kind whose content is free text rather than a row.
TEXT_ONLY_KIND = 'custom'


def _subject_name(topic):
    """The subject's name, for a label, however incomplete the tagging is."""
    if topic and topic.subject:
        return topic.subject.name
    return "No Subject"


def _subject_slug(topic):
    """The subject's slug, for a URL. Falls back to maths, as the middleware does."""
    if topic and topic.subject:
        return topic.subject.slug
    return 'maths'


def content_object(kind, refs):
    """The row this kind points at, or None for a written exercise."""
    field = CONTENT_FK_FIELDS.get(kind)
    return refs.get(field) if field else None


def content_display(kind, refs, instructions=''):
    """A label naming the content the way a teacher would say it aloud."""
    section = refs.get('section')
    exam_question = refs.get('exam_question')
    part = refs.get('exam_question_part')
    quickkick = refs.get('quickkick')
    flashcard_set = refs.get('flashcard_set')

    if kind == 'section' and section:
        topic = section.topic
        return (f"Practice Questions: {topic.name} > {section.name} "
                f"({_subject_name(topic)})")

    if kind == 'exam_question' and exam_question:
        paper = exam_question.exam_paper
        subject = paper.subject.name if paper and paper.subject else "No Subject"
        year = paper.year if paper else "Unknown"
        topic = exam_question.topic.name if exam_question.topic else "No Topic"
        return f"[{subject}] {year} - Q{exam_question.question_number} - {topic}"

    if kind == 'exam_part' and part:
        paper = part.question.exam_paper
        subject = paper.subject.name if paper and paper.subject else "No Subject"
        topic = part.topic.name if part.topic else "No Topic"
        return (f"[{subject}] {paper.year} {paper.get_paper_type_display()} - "
                f"Q{part.question.question_number}{part.label} - {topic}")

    if kind == 'quickkick' and quickkick:
        topic = quickkick.topic
        return (f"QuickFlicks: {topic.name} > {quickkick.title} "
                f"({_subject_name(topic)})")

    if kind == 'flashcard' and flashcard_set:
        topic = flashcard_set.topic
        card_count = flashcard_set.cards.count()
        return (f"Flashcards: {topic.name} > {flashcard_set.title} "
                f"({card_count} cards, {_subject_name(topic)})")

    if kind == TEXT_ONLY_KIND and instructions:
        return instructions

    return "Unknown task"


def content_url(kind, refs):
    """Where to send the student so they land on the work itself."""
    section = refs.get('section')
    exam_question = refs.get('exam_question')
    part = refs.get('exam_question_part')
    quickkick = refs.get('quickkick')
    flashcard_set = refs.get('flashcard_set')

    if kind == 'section' and section:
        topic = section.topic
        return (f"/interactive/{topic.slug}/sections/{section.slug}/"
                f"?subject={_subject_slug(topic)}")

    if kind == 'exam_question' and exam_question:
        # No GET route opens one whole question, so link to the topic's exam
        # page and anchor on the card -- see topic_exam_questions.html.
        topic = exam_question.topic
        if topic:
            return (f"/interactive/{topic.slug}/exam-questions/"
                    f"?subject={_subject_slug(topic)}#question-{exam_question.id}")
        return "/exam-papers/"

    if kind == 'exam_part' and part:
        # practise_part exists precisely so a link, not a form, can open a part.
        return reverse('exam_papers:practise_part', args=[part.pk])

    if kind == 'quickkick' and quickkick:
        topic = quickkick.topic
        return (f"/quickkicks/{topic.slug}/{quickkick.id}/"
                f"?subject={_subject_slug(topic)}")

    if kind == 'flashcard' and flashcard_set:
        topic = flashcard_set.topic
        return f"/flashcards/{topic.slug}/?subject={_subject_slug(topic)}"

    return "#"


#: The error raised when a kind's own foreign key is missing, keyed by kind.
MISSING_REF_ERRORS = {
    'section': ('section', 'Section is required when task type is "section"'),
    'exam_question': ('exam_question',
                      'Exam question is required when task type is "exam_question"'),
    'exam_part': ('exam_question_part',
                  'Exam question part is required when task type is "exam_part"'),
    'quickkick': ('quickkick', 'QuickFlicks is required when task type is "quickkick"'),
    'flashcard': ('flashcard_set',
                  'Flashcard set is required when task type is "flashcard"'),
}


def validate_refs(kind, refs, instructions=''):
    """{field: message} for what this kind needs and has not got.

    Returns a dict rather than raising, so the caller decides whether it is a
    ValidationError on a model or a warning on a preview page.
    """
    if kind in MISSING_REF_ERRORS:
        field, message = MISSING_REF_ERRORS[kind]
        if not refs.get(field):
            return {field: message}
        return {}

    if kind == TEXT_ONLY_KIND and not (instructions or '').strip():
        return {'instructions': 'Exercise text is required for a written exercise'}

    return {}


def null_unmatched(kind, obj):
    """Clear every content foreign key except the one this kind uses.

    Changing a task's kind must not leave the old row attached: it would keep a
    reference alive that the label and the URL no longer mention.
    """
    for field_kind, field in CONTENT_FK_FIELDS.items():
        if field_kind != kind:
            setattr(obj, field, None)


def refs_from(obj):
    """The five content foreign keys off a model instance, as a dict."""
    return {field: getattr(obj, field, None) for field in CONTENT_FK_FIELDS.values()}
