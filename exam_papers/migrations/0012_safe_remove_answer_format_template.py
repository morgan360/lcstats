# Generated migration with defensive column checks
from django.db import migrations


def safe_remove_field(apps, schema_editor):
    """
    Safely remove answer_format_template field only if it exists.
    Prevents migration errors on fresh installations.
    """
    from django.db import connection

    with connection.cursor() as cursor:
        # Check if answer_format_template_id column exists in exam_papers_examquestionpart
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'exam_papers_examquestionpart'
            AND COLUMN_NAME = 'answer_format_template_id'
        """)
        column_exists = cursor.fetchone()[0] > 0

        if column_exists:
            # Column exists, safe to drop it
            cursor.execute("""
                ALTER TABLE exam_papers_examquestionpart
                DROP FOREIGN KEY exam_papers_examque_answer_format_templ_3f8b0e31_fk_exam_pape
            """)
            cursor.execute("""
                ALTER TABLE exam_papers_examquestionpart
                DROP COLUMN answer_format_template_id
            """)

        # Check if the AnswerFormatTemplate table exists
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = DATABASE()
            AND TABLE_NAME = 'exam_papers_answerformattemplate'
        """)
        table_exists = cursor.fetchone()[0] > 0

        if table_exists:
            # Table exists, safe to drop it
            cursor.execute("DROP TABLE exam_papers_answerformattemplate")


def reverse_migration(apps, schema_editor):
    """
    Reverse is a no-op since we can't safely recreate removed fields.
    """
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('exam_papers', '0011_make_max_marks_optional'),
    ]

    operations = [
        migrations.RunPython(safe_remove_field, reverse_migration),
    ]