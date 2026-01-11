# Manual migration to fix Django's state after RunPython field removal
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('exam_papers', '0015_merge_20260111_1213'),
    ]

    operations = [
        # These fields were already removed by migration 0013's RunPython,
        # but we need to tell Django's state tracker they're gone
        migrations.SeparateDatabaseAndState(
            database_operations=[],  # No actual database changes needed
            state_operations=[
                migrations.RemoveField(
                    model_name='examquestionpart',
                    name='answer_format_template',
                ),
                migrations.RemoveField(
                    model_name='examquestionpart',
                    name='answer',
                ),
                migrations.RemoveField(
                    model_name='examquestionpart',
                    name='expected_format',
                ),
                migrations.RemoveField(
                    model_name='examquestionpart',
                    name='expected_type',
                ),
                migrations.RemoveField(
                    model_name='examquestionpart',
                    name='image',
                ),
                migrations.RemoveField(
                    model_name='examquestionpart',
                    name='solution',
                ),
                migrations.DeleteModel(
                    name='AnswerFormatTemplate',
                ),
            ],
        ),
    ]