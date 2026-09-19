"""Swap the part-topics M2M for a single topic FK.

Parts carried a set of topics for a few days. Not one part in the database
ever held two, and the tagging surface was too fine to keep correct by hand,
so a part now files under the one topic carrying most of its marks.

The whole swap happens in one migration because the new FK wants the
related_name the M2M currently owns; an intermediate state with both would be
an invalid model state (clashing reverse accessors).

One-way in practice: the reverse is a no-op, because the set a part used to
carry cannot be reconstructed from the one that survives. The safety net is a
database dump taken before this runs, not `migrate --backwards`.
"""
from django.db import migrations, models
import django.db.models.deletion


BATCH = 500


def backfill(apps, schema_editor):
    """Give every part one topic: its first, else its question's, else none.

    The through table has no explicit ordering, so "first by through-table id"
    is insertion order -- the classifier wrote the main topic first, which
    makes this the closest thing to the majority topic that survives.
    """
    ExamQuestionPart = apps.get_model('exam_papers', 'ExamQuestionPart')
    Through = ExamQuestionPart.topics.through

    # One pass over the through table rather than part.topics.all() per row:
    # production has many papers and this touches every part.
    first = {}
    for part_id, topic_id in (Through.objects.order_by('id')
                              .values_list('examquestionpart_id', 'topic_id')):
        first.setdefault(part_id, topic_id)

    pending = []
    parts = ExamQuestionPart.objects.values_list('id', 'question__topic_id')
    for part_id, question_topic_id in parts.iterator():
        topic_id = first.get(part_id) or question_topic_id
        if topic_id:
            pending.append(ExamQuestionPart(id=part_id, topic_id=topic_id))

    for start in range(0, len(pending), BATCH):
        ExamQuestionPart.objects.bulk_update(
            pending[start:start + BATCH], ['topic_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('interactive_lessons', '0031_assign_topic_papers'),
        ('exam_papers', '0021_examquestionpart_topics'),
    ]

    operations = [
        # Added under a temporary related_name so it can coexist with the M2M
        # for the one operation it takes to copy the data across.
        migrations.AddField(
            model_name='examquestionpart',
            name='topic',
            field=models.ForeignKey(
                blank=True,
                help_text="The topic carrying most of this part's marks",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='parts_topic_tmp',
                to='interactive_lessons.topic',
            ),
        ),
        migrations.RunPython(backfill, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='examquestionpart',
            name='topics',
        ),
        # State only -- the column is already there. This just takes the
        # related_name the M2M has now given up, so makemigrations --check
        # agrees with models.py.
        migrations.AlterField(
            model_name='examquestionpart',
            name='topic',
            field=models.ForeignKey(
                blank=True,
                help_text="The topic carrying most of this part's marks",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='exam_question_parts',
                to='interactive_lessons.topic',
            ),
        ),
    ]
