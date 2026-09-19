"""Somewhere to keep a merged part's second and later marking-scheme crops.

Kept apart from 0022 so that either can be re-run against a restored dump
without dragging the other along: 0022 rewrites every part row, this one only
creates a table.
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('exam_papers', '0022_examquestionpart_topic'),
    ]

    operations = [
        migrations.CreateModel(
            name='ExamPartSolutionImage',
            fields=[
                ('id', models.BigAutoField(
                    auto_created=True, primary_key=True, serialize=False,
                    verbose_name='ID')),
                ('image', models.ImageField(
                    help_text='A further marking-scheme crop for this part',
                    upload_to='exam_papers/marking_schemes/')),
                ('order', models.PositiveIntegerField(
                    default=0,
                    help_text="Reading order after the part's primary crop")),
                ('part', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='extra_solution_images',
                    to='exam_papers.examquestionpart')),
            ],
            options={
                'ordering': ['part', 'order', 'id'],
            },
        ),
    ]
