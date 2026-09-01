from django.apps import AppConfig


class HomeworkCheckConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'homework_check'
    verbose_name = 'Homework Check'

    def ready(self):
        from . import signals  # noqa: F401
