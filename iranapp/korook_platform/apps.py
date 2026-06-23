from django.apps import AppConfig


class PlatformConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "korook_platform"

    def ready(self):
        from . import signals  # noqa: F401
