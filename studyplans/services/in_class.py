"""Exam questions a teacher went through in class.

A question worked through on the board with the class is done, for every
student who was in the room, so the teacher ticks it off for them in one go.
It then counts like any other finished item, towards the MicroBadge it sits
in. That is the point: the plan should not keep asking a student to do a
question they have already seen worked.

"Classmates" are the students whose plans in the same class have the same
question. A class rollout copies one plan per student, so the same question
sits in each of their plans as a separate item.
"""
from collections import defaultdict

from django.db.models import Q
from django.utils import timezone

from ..models import StudyPlanEvent, StudyPlanItem
from . import microbadges

#: Only exam work can be marked done in class.
KINDS = ('exam_question', 'exam_part')


def can_mark(item):
    return item.content_type in KINDS and item.status not in ('done', 'skipped')


def matching_items(item, include_class=True):
    """This item and the same question in classmates' plans, by student name.

    Archived plans and removed (skipped) items are left out. Items already
    done are included, so the page can show they are done, not offer them.
    """
    field = 'exam_question_id' if item.content_type == 'exam_question' else 'exam_question_part_id'
    plan = item.plan
    items = StudyPlanItem.objects.filter(
        content_type=item.content_type, **{field: getattr(item, field)}
    ).exclude(status='skipped').exclude(plan__status='archived')
    if include_class and plan.teacher_class_id:
        items = items.filter(plan__teacher_class_id=plan.teacher_class_id)
    else:
        items = items.filter(plan=plan)
    return list(items.select_related('plan__student', 'micro_badge', 'goal__topic')
                .order_by('plan__student__first_name', 'plan__student__last_name',
                          'plan__student__username'))


def mark_done(items, when=None):
    """Tick these items off as done in class. Returns the items changed.

    Done is final here, as with the student's own tick: the nightly run never
    re-evaluates a done item, and finishing a MicroBadge's last item earns it.
    """
    when = when or timezone.now()
    note = f"Done in class · {timezone.localtime(when):%-d %b}"
    changed = []
    for item in items:
        if not can_mark(item):
            continue
        item.status = 'done'
        item.completed_at = when
        item.evidence_note = note
        item.needs_teacher_attention = False
        item.save(update_fields=['status', 'completed_at', 'evidence_note',
                                 'needs_teacher_attention', 'updated_at'])
        StudyPlanEvent.log(item.plan, 'teacher_edit',
                           f"Done in class: {item.get_content_display()}", item=item)
        changed.append(item)
    microbadges.award(microbadges.goals_of(changed), when=when)
    return changed


# ---------------------------------------------------------------------------
# By question, for a whole class: the papers-by-questions grid
# ---------------------------------------------------------------------------

def _class_items(teacher_class):
    """Live exam items in the class's current plans, for its current students."""
    return (StudyPlanItem.objects
            .filter(plan__teacher_class=teacher_class,
                    plan__student__in=teacher_class.students.all(),
                    content_type__in=KINDS)
            .exclude(status='skipped')
            .exclude(plan__status='archived'))


def _for_question(items, question):
    """Whole-question items, plus the older single-part ones of that question."""
    return items.filter(Q(content_type='exam_question', exam_question=question)
                        | Q(content_type='exam_part', exam_question_part__question=question))


def question_items(teacher_class, question):
    """Every student's items for this question, keyed by student id."""
    by_student = defaultdict(list)
    for item in _for_question(_class_items(teacher_class), question).select_related(
            'plan', 'micro_badge', 'exam_question_part'):
        by_student[item.plan.student_id].append(item)
    return by_student


def coverage(teacher_class):
    """{question_id: (students done, students with it on their plan)}.

    A student counts as done once every one of their items for the question
    is done -- normally there is one.
    """
    pending, seen = defaultdict(set), defaultdict(set)
    rows = _class_items(teacher_class).values_list(
        'plan__student_id', 'status', 'exam_question_id', 'exam_question_part__question_id')
    for student_id, status, question_id, part_question_id in rows:
        question_id = question_id or part_question_id
        seen[question_id].add(student_id)
        if status != 'done':
            pending[question_id].add(student_id)
    return {qid: (len(students - pending[qid]), len(students))
            for qid, students in seen.items()}
