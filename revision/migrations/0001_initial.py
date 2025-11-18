# Generated manually for revision app

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('interactive_lessons', '0001_initial'),  # Depends on Topic model
    ]

    operations = [
        migrations.CreateModel(
            name='RevisionModule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True, help_text='Brief overview of what this revision module covers')),
                ('is_published', models.BooleanField(default=False, help_text='Make visible to students')),
                ('order', models.IntegerField(default=0, help_text='Display order (lower numbers appear first)')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('topic', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='revision_module', to='interactive_lessons.topic')),
            ],
            options={
                'verbose_name': 'Revision Module',
                'verbose_name_plural': 'Revision Modules',
                'ordering': ['order', 'title'],
            },
        ),
        migrations.CreateModel(
            name='RevisionSection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(help_text='Section heading', max_length=200)),
                ('order', models.IntegerField(default=0, help_text='Display order within the module')),
                ('text_content', models.TextField(blank=True, help_text='Main content - supports Markdown and LaTeX (use $...$ for inline math, $$...$$ for display math)')),
                ('image', models.ImageField(blank=True, help_text='Optional image for this section', null=True, upload_to='revision/images/')),
                ('image_caption', models.CharField(blank=True, max_length=200)),
                ('geogebra_enabled', models.BooleanField(default=False, help_text='Enable GeoGebra interactive visualization')),
                ('geogebra_material_id', models.CharField(blank=True, help_text="GeoGebra Material ID (e.g., 'abcd1234' from geogebra.org/m/abcd1234)", max_length=100)),
                ('geogebra_width', models.IntegerField(default=800, help_text='Width in pixels')),
                ('geogebra_height', models.IntegerField(default=600, help_text='Height in pixels')),
                ('geogebra_show_toolbar', models.BooleanField(default=False, help_text='Show GeoGebra toolbar to students')),
                ('geogebra_show_menu', models.BooleanField(default=False, help_text='Show GeoGebra menu bar to students')),
                ('video_enabled', models.BooleanField(default=False, help_text='Enable video embed')),
                ('video_url', models.URLField(blank=True, help_text='YouTube URL (e.g., https://www.youtube.com/watch?v=...) or direct video URL')),
                ('video_caption', models.CharField(blank=True, max_length=200)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('module', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sections', to='revision.revisionmodule')),
            ],
            options={
                'verbose_name': 'Revision Section',
                'verbose_name_plural': 'Revision Sections',
                'ordering': ['order'],
            },
        ),
    ]
