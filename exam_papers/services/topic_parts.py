"""Finding exam questions, and the parts within them, that bear on a topic.

A question files under one dominant topic but each of its parts carries its
own, so a question belongs on a topic's page if either says so. The parts are
what a student is actually sent to practise.
"""
from django.db.models import Prefetch, Q

from exam_papers.models import ExamQuestion, ExamQuestionAttempt, ExamQuestionPart


def topic_filter(topic, prefix=''):
    """Q matching a question - or, with prefix='question__', a part's question -
    that touches topic through its own topic or any of its parts'."""
    return (Q(**{f'{prefix}topic': topic})
            | Q(**{f'{prefix}parts__topic': topic}))


def questions_for_topic(topic, published_only=True):
    """Questions touching topic, with parts and their topics prefetched."""
    questions = ExamQuestion.objects.filter(topic_filter(topic))
    if published_only:
        questions = questions.filter(exam_paper__is_published=True)
    return (questions.distinct()
            .select_related('exam_paper', 'topic')
            .prefetch_related(Prefetch(
                'parts',
                queryset=ExamQuestionPart.objects.order_by('order', 'id')
                                                 .select_related('topic'),
            )))


def attach_matching_parts(questions, topic):
    """Set question.matching_parts to the parts tagged with topic.

    A question listed only through its own topic - its parts not yet tagged, or
    tagged elsewhere - gets an empty list and is offered whole.
    """
    for question in questions:
        question.matching_parts = question.parts_on_topic(topic)
    return questions


def best_part_attempts(user, parts):
    """{part_id: {'count', 'best'}} for this user's attempts, in one query."""
    summary = {}
    attempts = (ExamQuestionAttempt.objects
                .filter(exam_attempt__student=user, question_part__in=parts)
                .order_by('question_part_id', '-marks_awarded'))
    for attempt in attempts:
        entry = summary.setdefault(attempt.question_part_id,
                                   {'count': 0, 'best': attempt})
        entry['count'] += 1
    return summary
