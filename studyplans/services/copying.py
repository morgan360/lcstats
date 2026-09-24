"""Copy a plan, as the teacher has shaped it, onto another student.

Unlike a class rollout, which plans afresh against each student's history, a
copy keeps exactly the work the teacher chose: the same topics, the same items
in the same MicroBadges and order, and the same Badge Test parts. Only the
student's own progress is left behind -- the copy starts unticked, unearned and
unsat, as a draft for the teacher to adjust and hand over.
"""
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from core import content_links
from ..models import (
    StudyPlan, StudyPlanEvent, StudyPlanGoal, StudyPlanItem, StudyPlanMicroBadge,
)
from . import checkpoints as checkpoint_service
from . import microbadges


@transaction.atomic
def copy_plan(source, student, teacher, start_date=None):
    """A draft copy of ``source`` for ``student``, starting ``start_date``.

    The copy runs as many days as the source did, from ``start_date`` (today
    by default), so its MicroBadge target dates are spread afresh rather than
    carried over already overdue. Retry MicroBadges and their revisit work
    belong to how the source's student did, so they are not copied, and nor is
    anything the teacher removed.
    """
    start_date = start_date or timezone.localdate()
    deadline = start_date + timedelta(days=(source.deadline - source.start_date).days)
    plan = StudyPlan.objects.create(
        student=student, teacher=teacher, subject=source.subject,
        title=source.title, description=source.description,
        start_date=start_date, deadline=deadline,
        weekly_minutes=source.weekly_minutes, status='draft')
    targets = microbadges.target_dates(start_date, deadline)

    for old_goal in source.goals.all():
        goal = StudyPlanGoal.objects.create(
            plan=plan, topic=old_goal.topic,
            target_mastery=old_goal.target_mastery,
            checkpoint_size=old_goal.checkpoint_size,
            priority=old_goal.priority, order=old_goal.order)

        for old_badge in microbadges.core_badges(old_goal):
            target = targets[min(old_badge.number, len(targets)) - 1]
            badge = StudyPlanMicroBadge.objects.create(
                goal=goal, number=old_badge.number, kind='core',
                target_date=target)
            for old_item in old_badge.items.exclude(status='skipped').order_by('order', 'id'):
                item = StudyPlanItem(
                    plan=plan, goal=goal, micro_badge=badge,
                    content_type=old_item.content_type,
                    instructions=old_item.instructions,
                    estimated_minutes=old_item.estimated_minutes,
                    order=old_item.order, origin=old_item.origin,
                    available_from=start_date, due_date=max(target, start_date))
                for field in content_links.CONTENT_FK_FIELDS.values():
                    setattr(item, field, getattr(old_item, field))
                item.save()

        for old_checkpoint in old_goal.checkpoints.order_by('round'):
            parts = [p.exam_question_part
                     for p in old_checkpoint.parts.select_related('exam_question_part')]
            checkpoint_service.create_checkpoint(
                goal, parts=parts, round_number=old_checkpoint.round,
                status='locked')

    StudyPlanEvent.log(
        plan, 'created',
        f"Copied from {source.student.username}'s plan as a draft")
    return plan
