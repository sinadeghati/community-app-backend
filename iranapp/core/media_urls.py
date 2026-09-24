"""Build public HTTPS media URLs without leaking filesystem paths."""

from __future__ import annotations

from django.conf import settings
from django.core.files.storage import default_storage


def media_storage_name(file_or_name) -> str | None:
    if not file_or_name:
        return None
    if hasattr(file_or_name, "name"):
        name = file_or_name.name
    else:
        name = str(file_or_name)
    name = name.strip()
    if not name:
        return None
    # Guard against accidental absolute paths stored in the database.
    media_root = str(settings.MEDIA_ROOT).replace("\\", "/").rstrip("/")
    normalized = name.replace("\\", "/")
    if normalized.startswith(media_root + "/"):
        normalized = normalized[len(media_root) + 1 :]
    if normalized.startswith("/"):
        normalized = normalized.lstrip("/")
    if normalized.startswith("media/"):
        normalized = normalized[len("media/") :]
    return normalized


def absolute_media_url(request, file_or_name) -> str | None:
    name = media_storage_name(file_or_name)
    if not name:
        return None
    relative = default_storage.url(name)
    if not relative.startswith("/"):
        relative = f"/{relative.lstrip('/')}"
    media_url = settings.MEDIA_URL
    if not media_url.endswith("/"):
        media_url = f"{media_url}/"
    if not relative.startswith(media_url):
        relative = f"{media_url}{name}"
    absolute = request.build_absolute_uri(relative)
    forbidden = str(settings.MEDIA_ROOT).replace("\\", "/")
    if forbidden and forbidden in absolute:
        raise ValueError("Media URL must not include MEDIA_ROOT filesystem path.")
    if "/app/media/" in absolute or "/app/" in absolute and "/media/" in absolute:
        # Railway container path leak — rebuild from known public prefix only.
        absolute = request.build_absolute_uri(f"{media_url.rstrip('/')}/{name}")
    return absolute


def media_file_exists(file_or_name) -> bool:
    name = media_storage_name(file_or_name)
    if not name:
        return False
    return default_storage.exists(name)
