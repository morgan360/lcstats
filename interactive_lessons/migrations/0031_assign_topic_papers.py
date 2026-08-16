"""Assign the Maths topics to Paper 1 or Paper 2.

Keyed on topic name and subject, never on primary key: ids differ between the
local database and production, so a pk-based migration would assign the wrong
topics on one of them.

Only fills blanks. Re-running cannot undo a change made by hand in admin, and
the migration is safe to re-apply against a database where someone has already
moved a topic.
"""
from django.db import migrations

PAPER_1 = [
    "Algebra (1)",
    "Algebra-Inequalities and Factorisation",
    "Complex Numbers",
    "Differential Calculus",
    "Finance",
    "Functions",
    "Indices and Logs",
    "Integration",
    "Proof by Induction",
    "Sequences and Series",
]

PAPER_2 = [
    "Area & Volume",
    "Descriptive Statistics",
    "Geometry",
    "Geometry-Constructions",
    "Geometry-Theorems",
    "Inferential Statistics",
    "Probability",
    "The Circle",
    "The Line",
    "Trigonometry (1)",
    "Trigonometry (2)",
]


def assign(apps, schema_editor):
    Topic = apps.get_model("interactive_lessons", "Topic")
    for paper, names in (("p1", PAPER_1), ("p2", PAPER_2)):
        Topic.objects.filter(
            subject__name="Maths", name__in=names, paper=""
        ).update(paper=paper)


def unassign(apps, schema_editor):
    Topic = apps.get_model("interactive_lessons", "Topic")
    Topic.objects.filter(
        subject__name="Maths", name__in=PAPER_1 + PAPER_2
    ).update(paper="")


class Migration(migrations.Migration):

    dependencies = [
        ("interactive_lessons", "0030_alter_topic_options_topic_order_topic_paper"),
    ]

    operations = [
        migrations.RunPython(assign, unassign),
    ]
