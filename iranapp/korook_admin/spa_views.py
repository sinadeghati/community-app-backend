import os
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse
from django.views import View


class AdminSpaView(View):
    """Serve Korook admin SPA static build at /admin-app/."""

    def get(self, request, path=""):
        dist = Path(settings.ADMIN_PANEL_DIST)
        if not dist.exists():
            return HttpResponse(
                "Korook admin UI build not found. Run: cd admin-panel && npm run build",
                status=503,
                content_type="text/plain",
            )
        safe = path.strip("/")
        if safe:
            target = dist / safe
            if target.is_file():
                return FileResponse(open(target, "rb"))
        index = dist / "index.html"
        if not index.exists():
            raise Http404
        return FileResponse(open(index, "rb"), content_type="text/html")
