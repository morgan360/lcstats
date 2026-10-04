"""Seed each question's secondary and need-to-know topics from its parts.

Topics are ranked by the part marks they carry -- the same rule as
``tag_question_topics`` -- and only blank fields are filled. The secondary is
ticked to list the question only when it carries at least a third of the
marks, so topic pages keep the questions they meaningfully showed while
parts decided the listing.

Copied rather than imported: a migration must not depend on code that can
change after it.
"""
from collections import defaultdict

from django.db import migrations

LIST_SECONDARY_SHARE = 1 / 3


def seed(apps, schema_editor):
    ExamQuestion = apps.get_model('exam_papers', 'ExamQuestion')
    for question in ExamQuestion.objects.prefetch_related('parts'):
        marks, first_seen, total = defaultdict(int), {}, 0
        for order, part in enumerate(sorted(question.parts.all(),
                                            key=lambda p: (p.order, p.id))):
            if part.topic_id is None:
                continue
            weight = part.max_marks or 1
            marks[part.topic_id] += weight
            total += weight
            first_seen.setdefault(part.topic_id, order)
        if not marks:
            continue

        ranked = sorted(marks, key=lambda t: (-marks[t], first_seen[t]))
        if question.topic_id is None:
            question.topic_id = ranked[0]
        rest = [t for t in ranked if t != question.topic_id]
        if rest and question.secondary_topic_id is None:
            question.secondary_topic_id = rest[0]
            question.list_under_secondary = (
                marks[rest[0]] >= total * LIST_SECONDARY_SHARE)
        rest = [t for t in rest if t != question.secondary_topic_id]
        if rest and question.need_to_know_topic_id is None:
            question.need_to_know_topic_id = rest[0]
        question.save(update_fields=['topic', 'secondary_topic',
                                     'list_under_secondary', 'need_to_know_topic'])


class Migration(migrations.Migration):

    dependencies = [
        ('exam_papers', '0024_question_secondary_topics'),
    ]

    operations = [
        migrations.RunPython(seed, migrations.RunPython.noop),
    ]
