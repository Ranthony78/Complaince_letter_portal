from django.apps import AppConfig

class DocumentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.documents'  # or 'documents' if not in apps folder
    verbose_name = 'Document Management'