from rest_framework.response import Response
from rest_framework.views import APIView

from korook_platform.models import AdminAuditLog

from .mixins import AdminAPIMixin
from .pagination import AdminPageNumberPagination
from .serializers import AdminAuditLogSerializer


class AdminAuditLogListView(AdminAPIMixin, APIView):
    def get(self, request):
        qs = AdminAuditLog.objects.select_related("actor").order_by("-created_at")
        actor = request.query_params.get("actor")
        if actor:
            qs = qs.filter(actor_id=actor)
        object_type = request.query_params.get("object_type")
        if object_type:
            qs = qs.filter(object_type=object_type)
        action_type = request.query_params.get("action_type")
        if action_type:
            qs = qs.filter(action_type=action_type)
        paginator = AdminPageNumberPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(AdminAuditLogSerializer(page, many=True).data)


class AdminSettingsView(AdminAPIMixin, APIView):
    def get(self, request):
        return Response(
            {
                "platform_name": "Korook",
                "admin_version": "phase-1",
                "features": {
                    "billing": False,
                    "ai_moderation": False,
                    "advertiser_portal": False,
                },
            }
        )
