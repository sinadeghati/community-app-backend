from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import get_or_create_email_profile
from korook_admin.audit import log_admin_action
from korook_platform.models import BusinessClaim, ContentReport, Event, UserPlatformProfile
from listings.models import Listing

from .mixins import AdminAPIMixin
from .pagination import AdminPageNumberPagination
from .serializers import (
    AdminUserBusinessSummarySerializer,
    AdminUserClaimSummarySerializer,
    AdminUserDetailSerializer,
    AdminUserEventSummarySerializer,
    AdminUserListSerializer,
    AdminUserReportSummarySerializer,
)


def _user_queryset():
    return (
        User.objects.select_related(
            "platform_profile",
            "platform_profile__suspended_by",
            "email_profile",
        )
        .annotate(
            businesses_created_count=Count("listings", distinct=True),
            businesses_owned_count=Count("owned_listings", distinct=True),
            events_count=Count("owned_events", distinct=True),
            claims_count=Count("business_claims", distinct=True),
            reports_count=Count("reports_against", distinct=True),
        )
        .order_by("-date_joined")
    )


def _filter_users(queryset, request):
    search = (request.query_params.get("search") or "").strip()
    if search:
        queryset = queryset.filter(
            Q(username__icontains=search)
            | Q(email__icontains=search)
            | Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
        )
    role = request.query_params.get("role")
    if role:
        queryset = queryset.filter(platform_profile__role=role)
    account_status = request.query_params.get("account_status")
    if account_status:
        queryset = queryset.filter(platform_profile__account_status=account_status)
    email_verified = request.query_params.get("email_verified")
    if email_verified in ("true", "false"):
        queryset = queryset.filter(
            email_profile__email_verified=(email_verified == "true")
        )
    return queryset


def _protected_user_error(user, actor):
    if user.id == actor.id:
        return "You cannot perform this action on your own account."
    if user.is_superuser:
        return "Superuser accounts cannot be modified this way."
    if user.is_staff:
        return "Staff accounts cannot be modified this way."
    return None


class AdminUserListView(AdminAPIMixin, APIView):
    def get(self, request):
        qs = _filter_users(_user_queryset(), request)
        paginator = AdminPageNumberPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = AdminUserListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class AdminUserDetailView(AdminAPIMixin, APIView):
    def get(self, request, user_id):
        user = _user_queryset().filter(pk=user_id).first()
        if not user:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(AdminUserDetailSerializer(user).data)

    def patch(self, request, user_id):
        user = User.objects.filter(pk=user_id).first()
        if not user:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        profile, _ = UserPlatformProfile.objects.get_or_create(user=user)
        before = {
            "role": profile.role,
            "account_status": profile.account_status,
            "admin_note": profile.admin_note,
        }
        if "role" in request.data:
            profile.role = request.data["role"]
        if "account_status" in request.data:
            profile.account_status = request.data["account_status"]
        if "admin_note" in request.data:
            profile.admin_note = request.data["admin_note"]
        profile.save()
        after = {
            "role": profile.role,
            "account_status": profile.account_status,
            "admin_note": profile.admin_note,
        }
        log_admin_action(
            actor=request.user,
            action_type="user.update",
            object_type="user",
            object_id=user.id,
            summary=f"Updated user {user.username}",
            before_state=before,
            after_state=after,
        )
        return Response(AdminUserDetailSerializer(_user_queryset().get(pk=user_id)).data)


class AdminUserSuspendView(AdminAPIMixin, APIView):
    def post(self, request, user_id):
        return _set_user_status(request, user_id, UserPlatformProfile.AccountStatus.SUSPENDED)


class AdminUserUnsuspendView(AdminAPIMixin, APIView):
    def post(self, request, user_id):
        return _set_user_status(request, user_id, UserPlatformProfile.AccountStatus.ACTIVE)


def _set_user_status(request, user_id, status_value):
    user = User.objects.filter(pk=user_id).first()
    if not user:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
    if status_value == UserPlatformProfile.AccountStatus.SUSPENDED:
        protected = _protected_user_error(user, request.user)
        if protected:
            return Response({"detail": protected}, status=status.HTTP_403_FORBIDDEN)
    profile, _ = UserPlatformProfile.objects.get_or_create(user=user)
    before = profile.account_status
    profile.account_status = status_value
    if status_value == UserPlatformProfile.AccountStatus.SUSPENDED:
        profile.suspended_at = timezone.now()
        profile.suspended_by = request.user
        user.is_active = False
    else:
        profile.suspended_at = None
        profile.suspended_by = None
        user.is_active = True
    profile.save()
    user.save(update_fields=["is_active"])
    log_admin_action(
        actor=request.user,
        action_type="user.suspend" if status_value == UserPlatformProfile.AccountStatus.SUSPENDED else "user.unsuspend",
        object_type="user",
        object_id=user.id,
        summary=f"Set account_status={status_value} for {user.username}",
        before_state={"account_status": before},
        after_state={"account_status": status_value},
    )
    return Response({"success": True, "account_status": status_value})


class AdminUserVerifyEmailView(AdminAPIMixin, APIView):
    def post(self, request, user_id):
        user = User.objects.filter(pk=user_id).first()
        if not user:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        profile = get_or_create_email_profile(user)
        profile.mark_verified()
        log_admin_action(
            actor=request.user,
            action_type="user.verify_email",
            object_type="user",
            object_id=user.id,
            summary=f"Manually verified email for {user.username}",
        )
        return Response({"success": True, "email_verified": True})


class AdminUserUnverifyEmailView(AdminAPIMixin, APIView):
    def post(self, request, user_id):
        user = User.objects.filter(pk=user_id).first()
        if not user:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        profile = get_or_create_email_profile(user)
        profile.email_verified = False
        profile.email_verified_at = None
        profile.save(update_fields=["email_verified", "email_verified_at"])
        log_admin_action(
            actor=request.user,
            action_type="user.unverify_email",
            object_type="user",
            object_id=user.id,
            summary=f"Removed email verification for {user.username}",
        )
        return Response({"success": True, "email_verified": False})


class AdminUserBusinessesView(AdminAPIMixin, APIView):
    def get(self, request, user_id):
        qs = Listing.objects.filter(Q(user_id=user_id) | Q(owner_id=user_id)).order_by(
            "-created_at"
        )
        paginator = AdminPageNumberPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(
            AdminUserBusinessSummarySerializer(page, many=True).data
        )


class AdminUserEventsView(AdminAPIMixin, APIView):
    def get(self, request, user_id):
        qs = Event.objects.filter(owner_id=user_id).order_by("-starts_at")
        paginator = AdminPageNumberPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(
            AdminUserEventSummarySerializer(page, many=True).data
        )


class AdminUserClaimsView(AdminAPIMixin, APIView):
    def get(self, request, user_id):
        qs = BusinessClaim.objects.filter(requester_id=user_id).select_related(
            "listing"
        ).order_by("-created_at")
        paginator = AdminPageNumberPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(
            AdminUserClaimSummarySerializer(page, many=True).data
        )


class AdminUserReportsView(AdminAPIMixin, APIView):
    def get(self, request, user_id):
        qs = ContentReport.objects.filter(reported_user_id=user_id).order_by("-created_at")
        paginator = AdminPageNumberPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(
            AdminUserReportSummarySerializer(page, many=True).data
        )
