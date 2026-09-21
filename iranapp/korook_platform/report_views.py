from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .report_serializers import (
    ContentReportCreateResponseSerializer,
    ContentReportCreateSerializer,
)


class UserContentReportCreateView(APIView):
    """Authenticated users can submit content reports for admin moderation."""

    permission_classes = [IsAuthenticated]
    http_method_names = ["post"]

    def post(self, request):
        serializer = ContentReportCreateSerializer(
            data=request.data,
            context={"request": request},
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        report = serializer.save()
        return Response(
            ContentReportCreateResponseSerializer(report).data,
            status=status.HTTP_201_CREATED,
        )
