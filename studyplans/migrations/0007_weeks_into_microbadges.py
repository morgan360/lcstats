"""Give every existing plan's topics their ten MicroBadges.

Plans made before MicroBadges handed work out in weeks. Each goal gets ten core
MicroBadges, with target dates spread from the plan's start to a week before
its deadline, and its items -- in the order the weeks gave them -- shared out
between them by time, so each is roughly a tenth of the work. A MicroBadge
whose items are all already done is earned, as of the last of them.

Nothing is deleted: weeks stay in the table, unused, and skipped items stay
skipped, outside any MicroBadge. The planner's own helpers are copied rather
than imported, because a migration must not change meaning when they do.
"""
from datetime import timedelta

from django.db import migrations

SLOTS = 10
BUFFER_DAYS = 7


def target_dates(start_date, deadline, count=SLOTS):
    last = deadline - timedelta(days=BUFFER_DAYS)
    if last <= start_date:
        last = deadline
    span = (last - start_date).days
    return [start_date + timedelta(days=round(span * n / count))
            for n in range(1, count + 1)]


def bundle(items, count=SLOTS):
    groups = [[] for _ in range(count)]
    remaining = list(items)
    for index in range(count):
        groups_left = count - index
        if not remaining:
            break
        if len(remaining) <= groups_left:
            groups[index].append(remaining.pop(0))
            continue
        share = sum(i.estimated_minutes for i in remaining) / groups_left
        group, spent = groups[index], 0
        while remaining and len(remaining) > groups_left - 1:
            nxt = remaining[0]
            if group and spent + nxt.estimated_minutes / 2 > share:
                break
            group.append(remaining.pop(0))
            spent += nxt.estimated_minutes
    return groups


def forwards(apps, schema_editor):
    StudyPlanGoal = apps.get_model('studyplans', 'StudyPlanGoal')
    StudyPlanItem = apps.get_model('studyplans', 'StudyPlanItem')
    StudyPlanMicroBadge = apps.get_model('studyplans', 'StudyPlanMicroBadge')

    for goal in StudyPlanGoal.objects.select_related('plan'):
        if StudyPlanMicroBadge.objects.filter(goal=goal).exists():
            continue
        plan = goal.plan
        items = list(StudyPlanItem.objects
                     .filter(goal=goal)
                     .exclude(status='skipped')
                     .select_related('week')
                     .order_by('week__index', 'order', 'id'))
        # Backlog items (no week) go last, in their own order.
        items.sort(key=lambda i: (i.week is None, i.week.index if i.week else 0,
                                  i.order, i.id))

        for number, (target, group) in enumerate(
                zip(target_dates(plan.start_date, plan.deadline), bundle(items)),
                start=1):
            done = bool(group) and all(i.status == 'done' for i in group)
            badge = StudyPlanMicroBadge.objects.create(
                goal=goal, number=number, kind='core', target_date=target,
                earned_at=(max((i.completed_at for i in group if i.completed_at),
                               default=None) if done else None))
            if done and badge.earned_at is None:
                # Done but never stamped with a time: earned, as of the plan's
                # last update rather than left unearned on a technicality.
                badge.earned_at = plan.updated_at
                badge.save(update_fields=['earned_at'])
            for item in group:
                item.micro_badge = badge
                item.due_date = max(target, item.available_from)
                item.save(update_fields=['micro_badge', 'due_date'])


def backwards(apps, schema_editor):
    StudyPlanItem = apps.get_model('studyplans', 'StudyPlanItem')
    StudyPlanMicroBadge = apps.get_model('studyplans', 'StudyPlanMicroBadge')
    StudyPlanItem.objects.update(micro_badge=None)
    StudyPlanMicroBadge.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('studyplans', '0006_microbadges'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
