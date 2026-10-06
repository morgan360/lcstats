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

from ..models import QuestionCoverage, StudyPlanEvent, StudyPlanItem
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
#
# Independent of study plans: covering a question is its own record
# (QuestionCoverage), which inks the question on the student's exam stamp
# card. Where the question also sits in one of the student's plans, that
# item is ticked off too, so the plan does not ask for it again.
# ---------------------------------------------------------------------------

def coverage(teacher_class):
    """{question_id: number of the class's current students who covered it}."""
    counts = defaultdict(int)
    for question_id in (QuestionCoverage.objects
                        .filter(student__in=teacher_class.students.all())
                        .values_list('question_id', flat=True)):
        counts[question_id] += 1
    return counts


def covered_student_ids(teacher_class, question):
    return set(QuestionCoverage.objects
               .filter(question=question, student__in=teacher_class.students.all())
               .values_list('student_id', flat=True))


def set_coverage(teacher_class, question, student_ids, by, when=None):
    """Make the class's coverage of this question match the ticked students.

    Only the class's own students are touched. Returns (added, removed).
    Unticking removes the record, and with it the stamp, but never un-does a
    plan item: done is final there.
    """
    when = when or timezone.now()
    class_ids = set(teacher_class.students.values_list('id', flat=True))
    wanted = {int(i) for i in student_ids if str(i).isdigit()} & class_ids
    have = covered_student_ids(teacher_class, question)

    added = wanted - have
    removed = have - wanted
    QuestionCoverage.objects.bulk_create([
        QuestionCoverage(student_id=sid, question=question, covered_by=by,
                         teacher_class=teacher_class, covered_at=when)
        for sid in added
    ], ignore_conflicts=True)
    QuestionCoverage.objects.filter(question=question, student_id__in=removed).delete()

    if added:
        items = (StudyPlanItem.objects
                 .filter(plan__student_id__in=added)
                 .filter(Q(content_type='exam_question', exam_question=question)
                         | Q(content_type='exam_part', exam_question_part__question=question))
                 .exclude(status__in=('done', 'skipped'))
                 .exclude(plan__status='archived')
                 .select_related('plan'))
        mark_done(list(items), when=when)
    return added, removed
