from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        # Without this, every LaTeX render spawns a node process that crashes
        # on startup under uWSGI. See core/katex_warmup.py for the details.
        from .katex_warmup import warm_katex_options
        warm_katex_options()
