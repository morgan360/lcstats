# Generated migration to fix UTF8MB4 encoding for mathematical symbols
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('exam_papers', '0008_examquestionpart_answer_format_template_and_more'),
    ]

    operations = [
        migrations.RunSQL(
            # Convert all text fields in exam_papers tables to utf8mb4
            sql=[
                # ExamQuestionPart - answer, solution, expected_format
                "ALTER TABLE exam_papers_examquestionpart MODIFY answer LONGTEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;",
                "ALTER TABLE exam_papers_examquestionpart MODIFY solution LONGTEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;",
                "ALTER TABLE exam_papers_examquestionpart MODIFY expected_format LONGTEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;",

                # ExamPaper - instructions, title
                "ALTER TABLE exam_papers_exampaper MODIFY instructions LONGTEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;",
                "ALTER TABLE exam_papers_exampaper MODIFY title VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;",

                # ExamQuestion - title
                "ALTER TABLE exam_papers_examquestion MODIFY title VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;",

                # ExamQuestionAttempt - student_answer, feedback
                "ALTER TABLE exam_papers_examquestionattempt MODIFY student_answer LONGTEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;",
                "ALTER TABLE exam_papers_examquestionattempt MODIFY feedback LONGTEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;",

                # AnswerFormatTemplate - name, description, example, category
                "ALTER TABLE exam_papers_answerformattemplate MODIFY name VARCHAR(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;",
                "ALTER TABLE exam_papers_answerformattemplate MODIFY description LONGTEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;",
                "ALTER TABLE exam_papers_answerformattemplate MODIFY example VARCHAR(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;",
                "ALTER TABLE exam_papers_answerformattemplate MODIFY category VARCHAR(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;",
            ],
            reverse_sql=[
                # Reverse migrations (convert back to utf8, though this may cause data loss)
                "ALTER TABLE exam_papers_examquestionpart MODIFY answer LONGTEXT CHARACTER SET utf8 COLLATE utf8_general_ci;",
                "ALTER TABLE exam_papers_examquestionpart MODIFY solution LONGTEXT CHARACTER SET utf8 COLLATE utf8_general_ci;",
                "ALTER TABLE exam_papers_examquestionpart MODIFY expected_format LONGTEXT CHARACTER SET utf8 COLLATE utf8_general_ci;",
                "ALTER TABLE exam_papers_exampaper MODIFY instructions LONGTEXT CHARACTER SET utf8 COLLATE utf8_general_ci;",
                "ALTER TABLE exam_papers_exampaper MODIFY title VARCHAR(255) CHARACTER SET utf8 COLLATE utf8_general_ci;",
                "ALTER TABLE exam_papers_examquestion MODIFY title VARCHAR(255) CHARACTER SET utf8 COLLATE utf8_general_ci;",
                "ALTER TABLE exam_papers_examquestionattempt MODIFY student_answer LONGTEXT CHARACTER SET utf8 COLLATE utf8_general_ci;",
                "ALTER TABLE exam_papers_examquestionattempt MODIFY feedback LONGTEXT CHARACTER SET utf8 COLLATE utf8_general_ci;",
                "ALTER TABLE exam_papers_answerformattemplate MODIFY name VARCHAR(100) CHARACTER SET utf8 COLLATE utf8_general_ci;",
                "ALTER TABLE exam_papers_answerformattemplate MODIFY description LONGTEXT CHARACTER SET utf8 COLLATE utf8_general_ci;",
                "ALTER TABLE exam_papers_answerformattemplate MODIFY example VARCHAR(200) CHARACTER SET utf8 COLLATE utf8_general_ci;",
                "ALTER TABLE exam_papers_answerformattemplate MODIFY category VARCHAR(50) CHARACTER SET utf8 COLLATE utf8_general_ci;",
            ],
        ),
    ]