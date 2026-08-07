"""Give every flashcard a stable cross-database identifier.

Added in three steps because existing rows need distinct values before the
unique constraint can go on: add the column nullable, backfill a UUID per row,
then tighten it to unique and non-null.
"""

import uuid

from django.db import migrations, models

import flashcards.models


def backfill_external_ids(apps, schema_editor):
    Flashcard = apps.get_model('flashcards', 'Flashcard')
    for card in Flashcard.objects.filter(external_id__isnull=True).iterator():
        card.external_id = str(uuid.uuid4())
        card.save(update_fields=['external_id'])


def noop(apps, schema_editor):
    """Reversing just drops the column again, so nothing to undo here."""


class Migration(migrations.Migration):

    dependencies = [
        ('flashcards', '0002_alter_flashcardattempt_mastery_level'),
    ]

    operations = [
        migrations.AddField(
            model_name='flashcard',
            name='external_id',
            field=models.CharField(
                max_length=36, null=True, editable=False,
                help_text='Stable cross-database identifier, used to sync cards'),
        ),
        migrations.RunPython(backfill_external_ids, noop),
        migrations.AlterField(
            model_name='flashcard',
            name='external_id',
            field=models.CharField(
                max_length=36, unique=True, editable=False,
                default=flashcards.models.new_external_id,
                help_text='Stable cross-database identifier, used to sync cards'),
        ),
    ]
