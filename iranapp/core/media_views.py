"""Serve uploaded media in production when using local/volume-backed storage."""

import mimetypes
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404
from django.utils._os import safe_join
from django.views import View

from core.media_urls import media_file_exists, media_storage_name


class PublicMediaView(View):
    """Serve files under MEDIA_ROOT at MEDIA_URL (volume-backed on Railway)."""

    def get(self, request, path):
        if not getattr(settings, "SERVE_MEDIA", False):
            raise Http404()
        safe_name = media_storage_name(path)
        if not safe_name or not media_file_exists(safe_name):
            raise Http404()
        full_path = safe_join(str(settings.MEDIA_ROOT), safe_name)
        if not full_path or not Path(full_path).is_file():
            raise Http404()
        content_type, _ = mimetypes.guess_type(full_path)
        return FileResponse(open(full_path, "rb"), content_type=content_type or "application/octet-stream")
