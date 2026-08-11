# apps/letters/apps.py
from django.apps import AppConfig


class LettersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.letters'
    verbose_name = 'Letters Management'

    def ready(self):
        """Import signals when app is ready"""
        try:
            import apps.letters.signals
        except ImportError:
            pass