from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from korook_admin.audit import log_admin_action
from listings.models import Listing, ListingImage
from korook_platform.models import ContentReport, Event, UserPlatformProfile

from .mixins import AdminAPIMixin
from .pagination import AdminPageNumberPagination
from .serializers import ContentReportAdminSerializer


class AdminReportListView(AdminAPIMixin, APIView):
    def get(self, request):
        qs = ContentReport.objects.order_by("-created_at")
        status_val = request.query_params.get("status")
        if status_val:
            qs = qs.filter(status=status_val)
        object_type = request.query_params.get("object_type")
        if object_type:
            qs = qs.filter(reported_object_type=object_type)
        object_id = request.query_params.get("object_id")
        if object_id:
            qs = qs.filter(reported_object_id=object_id)
        paginator = AdminPageNumberPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(
            ContentReportAdminSerializer(page, many=True).data
        )


class AdminReportDetailView(AdminAPIMixin, APIView):
    def get(self, request, report_id):
        report = ContentReport.objects.filter(pk=report_id).first()
        if not report:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(ContentReportAdminSerializer(report).data)

    def patch(self, request, report_id):
        report = ContentReport.objects.filter(pk=report_id).first()
        if not report:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        for field in ("status", "admin_note", "action_taken"):
            if field in request.data:
                setattr(report, field, request.data[field])
        report.save()
        return Response(ContentReportAdminSerializer(report).data)


class AdminReportActionView(AdminAPIMixin, APIView):
    def post(self, request, report_id, action):
        report = ContentReport.objects.filter(pk=report_id).first()
        if not report:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if action == "hide-content":
            _hide_report_target(report)
            report.action_taken = ContentReport.ActionTaken.HIDE
        elif action == "delete-content":
            _delete_report_target(report)
            report.action_taken = ContentReport.ActionTaken.DELETE
        elif action == "restore-content":
            _restore_report_target(report)
            report.action_taken = ContentReport.ActionTaken.RESTORE
        elif action == "suspend-user":
            if report.reported_user_id:
                profile, _ = UserPlatformProfile.objects.get_or_create(
                    user=report.reported_user
                )
                profile.account_status = UserPlatformProfile.AccountStatus.SUSPENDED
                profile.suspended_at = timezone.now()
                profile.suspended_by = request.user
                profile.save()
                report.reported_user.is_active = False
                report.reported_user.save(update_fields=["is_active"])
            report.action_taken = ContentReport.ActionTaken.SUSPEND_USER
        elif action == "mark-reviewed":
            report.status = ContentReport.Status.ACTIONED
        elif action == "dismiss":
            report.status = ContentReport.Status.DISMISSED
        else:
            return Response({"detail": "Unknown action."}, status=status.HTTP_400_BAD_REQUEST)

        report.reviewed_by = request.user
        report.reviewed_at = timezone.now()
        if report.status == ContentReport.Status.NEW:
            report.status = ContentReport.Status.IN_REVIEW
        if action in ("mark-reviewed", "dismiss"):
            report.status = (
                ContentReport.Status.DISMISSED
                if action == "dismiss"
                else ContentReport.Status.ACTIONED
            )
        report.admin_note = request.data.get("admin_note", report.admin_note)
        report.save()
        log_admin_action(
            actor=request.user,
            action_type=f"report.{action}",
            object_type="content_report",
            object_id=report.id,
            summary=f"Report {action} on {report.reported_object_type}:{report.reported_object_id}",
            admin_note=report.admin_note,
        )
        return Response(ContentReportAdminSerializer(report).data)


def _hide_report_target(report):
    if report.listing_id:
        report.listing.status = Listing.Status.HIDDEN
        report.listing.save(update_fields=["status", "updated_at"])
    elif report.event_id:
        report.event.status = Event.Status.HIDDEN
        report.event.save(update_fields=["status", "updated_at"])
    elif report.listing_image_id:
        report.listing_image.media_status = ListingImage.MediaStatus.HIDDEN
        report.listing_image.save(update_fields=["media_status"])


def _delete_report_target(report):
    if report.listing_id:
        report.listing.delete()
    elif report.event_id:
        report.event.delete()
    elif report.listing_image_id:
        report.listing_image.delete()


def _restore_report_target(report):
    if report.listing_id:
        report.listing.status = Listing.Status.PUBLISHED
        report.listing.save(update_fields=["status", "updated_at"])
    elif report.event_id:
        report.event.status = Event.Status.PUBLISHED
        report.event.save(update_fields=["status", "updated_at"])
    elif report.listing_image_id:
        report.listing_image.media_status = ListingImage.MediaStatus.ACTIVE
        report.listing_image.save(update_fields=["media_status"])
