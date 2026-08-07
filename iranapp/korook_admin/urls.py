from django.urls import path

from .audit_views import AdminAuditLogListView, AdminSettingsView
from .auth_views import AdminLoginView, AdminLogoutView, AdminMeView
from .csrf_views import AdminCsrfView
from .business_image_views import (
    AdminBusinessImageActionView,
    AdminBusinessImageDetailView,
    AdminBusinessImageReorderView,
    AdminBusinessImageView,
)
from .business_views import (
    AdminBusinessActionView,
    AdminBusinessDetailView,
    AdminBusinessListCreateView,
    AdminPremiumListingsView,
)
from .claim_views import (
    AdminClaimApproveView,
    AdminClaimDetailView,
    AdminClaimListView,
    AdminClaimRejectView,
)
from .dashboard_views import DashboardStatsView
from .event_views import AdminEventActionView, AdminEventDetailView, AdminEventListCreateView
from .media_views import AdminEventCoverMediaView, AdminMediaActionView, AdminMediaListView
from .promotion_views import (
    AdminPromotionActionView,
    AdminPromotionDetailView,
    AdminPromotionListCreateView,
)
from .report_views import AdminReportActionView, AdminReportDetailView, AdminReportListView
from .user_views import (
    AdminUserBusinessesView,
    AdminUserClaimsView,
    AdminUserDetailView,
    AdminUserEventsView,
    AdminUserListView,
    AdminUserReportsView,
    AdminUserSuspendView,
    AdminUserUnsuspendView,
    AdminUserUnverifyEmailView,
    AdminUserVerifyEmailView,
)

urlpatterns = [
    path("auth/csrf/", AdminCsrfView.as_view(), name="admin-auth-csrf"),
    path("auth/login/", AdminLoginView.as_view(), name="admin-auth-login"),
    path("auth/logout/", AdminLogoutView.as_view(), name="admin-auth-logout"),
    path("auth/me/", AdminMeView.as_view(), name="admin-auth-me"),
    path("dashboard/stats/", DashboardStatsView.as_view(), name="admin-dashboard-stats"),
    path("users/", AdminUserListView.as_view(), name="admin-users-list"),
    path("users/<int:user_id>/", AdminUserDetailView.as_view(), name="admin-users-detail"),
    path("users/<int:user_id>/suspend/", AdminUserSuspendView.as_view(), name="admin-users-suspend"),
    path("users/<int:user_id>/unsuspend/", AdminUserUnsuspendView.as_view(), name="admin-users-unsuspend"),
    path("users/<int:user_id>/verify-email/", AdminUserVerifyEmailView.as_view(), name="admin-users-verify-email"),
    path("users/<int:user_id>/unverify-email/", AdminUserUnverifyEmailView.as_view(), name="admin-users-unverify-email"),
    path("users/<int:user_id>/businesses/", AdminUserBusinessesView.as_view(), name="admin-users-businesses"),
    path("users/<int:user_id>/events/", AdminUserEventsView.as_view(), name="admin-users-events"),
    path("users/<int:user_id>/claims/", AdminUserClaimsView.as_view(), name="admin-users-claims"),
    path("users/<int:user_id>/reports/", AdminUserReportsView.as_view(), name="admin-users-reports"),
    path("businesses/", AdminBusinessListCreateView.as_view(), name="admin-businesses-list"),
    path("businesses/<int:business_id>/", AdminBusinessDetailView.as_view(), name="admin-businesses-detail"),
    path("businesses/<int:business_id>/images/", AdminBusinessImageView.as_view(), name="admin-businesses-images"),
    path(
        "businesses/<int:business_id>/images/reorder/",
        AdminBusinessImageReorderView.as_view(),
        name="admin-businesses-images-reorder",
    ),
    path(
        "businesses/<int:business_id>/images/<int:image_id>/",
        AdminBusinessImageDetailView.as_view(),
        name="admin-businesses-images-detail",
    ),
    path(
        "businesses/<int:business_id>/images/<int:image_id>/<str:action>/",
        AdminBusinessImageActionView.as_view(),
        name="admin-businesses-images-action",
    ),
    path(
        "businesses/<int:business_id>/<str:action>/",
        AdminBusinessActionView.as_view(),
        name="admin-businesses-action",
    ),
    path("premium-listings/", AdminPremiumListingsView.as_view(), name="admin-premium-listings"),
    path("events/", AdminEventListCreateView.as_view(), name="admin-events-list"),
    path("events/<int:event_id>/", AdminEventDetailView.as_view(), name="admin-events-detail"),
    path(
        "events/<int:event_id>/<str:action>/",
        AdminEventActionView.as_view(),
        name="admin-events-action",
    ),
    path("promotions/", AdminPromotionListCreateView.as_view(), name="admin-promotions-list"),
    path("promotions/<int:promotion_id>/", AdminPromotionDetailView.as_view(), name="admin-promotions-detail"),
    path(
        "promotions/<int:promotion_id>/<str:action>/",
        AdminPromotionActionView.as_view(),
        name="admin-promotions-action",
    ),
    path("claims/", AdminClaimListView.as_view(), name="admin-claims-list"),
    path("claims/<int:claim_id>/", AdminClaimDetailView.as_view(), name="admin-claims-detail"),
    path("claims/<int:claim_id>/approve/", AdminClaimApproveView.as_view(), name="admin-claims-approve"),
    path("claims/<int:claim_id>/reject/", AdminClaimRejectView.as_view(), name="admin-claims-reject"),
    path("reports/", AdminReportListView.as_view(), name="admin-reports-list"),
    path("reports/<int:report_id>/", AdminReportDetailView.as_view(), name="admin-reports-detail"),
    path(
        "reports/<int:report_id>/<str:action>/",
        AdminReportActionView.as_view(),
        name="admin-reports-action",
    ),
    path("media/", AdminMediaListView.as_view(), name="admin-media-list"),
    path("media/<int:media_id>/<str:action>/", AdminMediaActionView.as_view(), name="admin-media-action"),
    path(
        "event-media/<int:event_id>/<str:action>/",
        AdminEventCoverMediaView.as_view(),
        name="admin-event-media-action",
    ),
    path("audit-log/", AdminAuditLogListView.as_view(), name="admin-audit-log"),
    path("settings/", AdminSettingsView.as_view(), name="admin-settings"),
]
