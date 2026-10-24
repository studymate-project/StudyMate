from django.apps import AppConfig


class ResourcesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.resources"

    def ready(self):
        from . import subject_cache_signals  # noqa: F401
