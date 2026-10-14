"""Finding the exam questions listed under a topic.

A question is listed under its main topic, and under its secondary topic when
``list_under_secondary`` is ticked. Its need-to-know topic is shown on the
question but never lists it: a question that only leans on a topic is not
practice for that topic.
"""
from django.db.models import Prefetch, Q

from exam_papers.models import (
    ExamQuestion, ExamQuestionAttempt, ExamQuestionPart, QuestionRestart,
)


def topic_filter(topic, prefix=''):
    """Q matching a question - or, with prefix='question__', a part's question -
    listed under topic."""
    return (Q(**{f'{prefix}topic': topic})
            | Q(**{f'{prefix}secondary_topic': topic,
                   f'{prefix}list_under_secondary': True}))


def questions_for_topic(topic, published_only=True):
    """Questions listed under topic, with their parts and topics prefetched."""
    questions = ExamQuestion.objects.filter(topic_filter(topic))
    if published_only:
        questions = questions.filter(exam_paper__is_published=True)
    return (questions.distinct()
            .select_related('exam_paper', 'topic', 'secondary_topic',
                            'need_to_know_topic')
            .prefetch_related(Prefetch(
                'parts', queryset=ExamQuestionPart.objects.order_by('order', 'id'),
            )))


def best_part_attempts(user, parts):
    """{part_id: {'count', 'best'}} for this user's attempts, in one query.

    A question started over in practice forgets that attempt's earlier
    answers here, as it does on the question page (ExamAttempt.answers_to):
    a 15/15 from before the restart is not the score to show after it.
    """
    summary = {}
    attempts = (ExamQuestionAttempt.objects
                .filter(exam_attempt__student=user, question_part__in=parts)
                .select_related('question_part')
                .order_by('question_part_id', '-marks_awarded'))
    restarts = {
        (r.exam_attempt_id, r.question_id): r.restarted_at
        for r in QuestionRestart.objects.filter(exam_attempt__student=user)
    }
    for attempt in attempts:
        cutoff = restarts.get((attempt.exam_attempt_id, attempt.question_part.question_id))
        if cutoff and attempt.submitted_at <= cutoff:
            continue
        entry = summary.setdefault(attempt.question_part_id,
                                   {'count': 0, 'best': attempt})
        entry['count'] += 1
    return summary
