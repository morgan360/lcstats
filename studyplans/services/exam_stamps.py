"""Exam stamp cards: one row per past paper, a MicroBadge per question.

A question's MicroBadge is inked once the student has attempted every one of
its parts, in any mode and at any score. The paper's badge is inked once every
question on it has its MicroBadge. Unlike the topic cards this reads attempts
directly -- no plan is involved.

Deferred papers are left off. Reads only.
"""
from collections import defaultdict

from exam_papers.models import ExamPaper, ExamQuestionAttempt, ExamQuestionPart

#: Question columns on a row. LC Higher papers have ten questions; a paper
#: with fewer shows the rest as empty cells.
SLOTS = 10


def rows_for(user, subject=None):
    """[{'paper', 'cells', 'earned', 'total', 'stamped'}], newest paper first,
    Paper 1 before Paper 2."""
    papers = (ExamPaper.objects
              .filter(is_published=True, is_deferred=False)
              .prefetch_related('questions')
              .order_by('-year', 'paper_type'))
    if subject is not None:
        papers = papers.filter(subject=subject)
    papers = list(papers)

    parts_by_question = defaultdict(set)
    for question_id, part_id in (ExamQuestionPart.objects
                                 .filter(question__exam_paper__in=papers)
                                 .values_list('question_id', 'id')):
        parts_by_question[question_id].add(part_id)

    attempted = set(ExamQuestionAttempt.objects
                    .filter(exam_attempt__student=user,
                            question_part__question__exam_paper__in=papers)
                    .values_list('question_part_id', flat=True)
                    .distinct())

    rows = []
    for paper in papers:
        by_number = {q.question_number: q for q in paper.questions.all()}
        cells = []
        for number in range(1, SLOTS + 1):
            question = by_number.get(number)
            parts = parts_by_question.get(question.id, set()) if question else set()
            cells.append({
                'number': number,
                'question': question,
                'stamped': bool(parts) and parts <= attempted,
            })
        questions = [c for c in cells if c['question']]
        earned = sum(c['stamped'] for c in questions)
        rows.append({
            'paper': paper,
            'cells': cells,
            'earned': earned,
            'total': len(questions),
            'stamped': bool(questions) and earned == len(questions),
        })
    return rows
