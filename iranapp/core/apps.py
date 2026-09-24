from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        from django.conf import settings

        media_root = getattr(settings, "MEDIA_ROOT", None)
        if media_root:
            media_root.mkdir(parents=True, exist_ok=True)
            (media_root / "listings").mkdir(parents=True, exist_ok=True)
