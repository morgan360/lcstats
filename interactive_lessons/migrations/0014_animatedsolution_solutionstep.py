# Generated manually for animated step-by-step solutions

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('interactive_lessons', '0013_studentinquiry'),
    ]

    operations = [
        migrations.CreateModel(
            name='AnimatedSolution',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(blank=True, help_text='Optional title for the animated solution', max_length=200, null=True)),
                ('is_active', models.BooleanField(default=True, help_text='Whether this animated solution is active and visible to students')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('question_part', models.OneToOneField(help_text='Question part this animated solution belongs to', on_delete=django.db.models.deletion.CASCADE, related_name='animated_solution', to='interactive_lessons.questionpart')),
            ],
            options={
                'ordering': ('question_part__question__order', 'question_part__order'),
            },
        ),
        migrations.CreateModel(
            name='SolutionStep',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order', models.PositiveIntegerField(default=0, help_text='Order of this step in the sequence')),
                ('step_type', models.CharField(choices=[('text', 'Text Explanation'), ('calculation', 'Mathematical Calculation'), ('drawing', 'Drawing/Diagram'), ('geogebra', 'GeoGebra Interactive')], default='text', help_text='Type of content for this step', max_length=20)),
                ('explanation', models.TextField(help_text='Explanation text shown in speech bubble (supports LaTeX with \\(...\\) or $$...$$)')),
                ('calculation', models.TextField(blank=True, help_text='Mathematical calculation or formula (LaTeX format)', null=True)),
                ('drawing_image', models.ImageField(blank=True, help_text='Upload a diagram or drawing for this step', null=True, upload_to='solution_drawings/')),
                ('geogebra_id', models.CharField(blank=True, help_text="GeoGebra app ID (e.g., 'bnvqawfu' from geogebra.org/m/bnvqawfu)", max_length=100, null=True)),
                ('geogebra_settings', models.JSONField(blank=True, help_text='Optional GeoGebra settings (JSON format)', null=True)),
                ('notes', models.TextField(blank=True, help_text='Internal notes for teachers (not shown to students)', null=True)),
                ('animated_solution', models.ForeignKey(help_text='Animated solution this step belongs to', on_delete=django.db.models.deletion.CASCADE, related_name='steps', to='interactive_lessons.animatedsolution')),
            ],
            options={
                'ordering': ('animated_solution', 'order'),
            },
        ),
    ]
