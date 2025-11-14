# Generated manually to fix UserSession and LoginHistory schema
# This migration drops and recreates the tables with the correct schema

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('students', '0005_loginhistory_usersession'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Remove the old tables
        migrations.DeleteModel(
            name='UserSession',
        ),
        migrations.DeleteModel(
            name='LoginHistory',
        ),
        # Recreate LoginHistory with correct schema
        migrations.CreateModel(
            name='LoginHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('username_attempted', models.CharField(help_text='Username used in login attempt', max_length=150)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('success', models.BooleanField(default=True)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.TextField(blank=True, help_text='Browser/device information')),
                ('session_key', models.CharField(blank=True, max_length=40)),
                ('user', models.ForeignKey(blank=True, help_text='User who attempted to login (null for failed attempts)', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='login_history', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Login History',
                'verbose_name_plural': 'Login History',
                'ordering': ['-timestamp'],
            },
        ),
        # Recreate UserSession with correct schema (session_key as CharField)
        migrations.CreateModel(
            name='UserSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('session_key', models.CharField(help_text='Django session key', max_length=40, unique=True)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.TextField(blank=True)),
                ('login_time', models.DateTimeField(auto_now_add=True)),
                ('last_activity', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='active_sessions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Active Session',
                'verbose_name_plural': 'Active Sessions',
                'ordering': ['-last_activity'],
            },
        ),
        # Add indexes
        migrations.AddIndex(
            model_name='loginhistory',
            index=models.Index(fields=['-timestamp'], name='students_lo_timesta_a1e2cd_idx'),
        ),
        migrations.AddIndex(
            model_name='loginhistory',
            index=models.Index(fields=['user', '-timestamp'], name='students_lo_user_id_cb9d2f_idx'),
        ),
    ]
