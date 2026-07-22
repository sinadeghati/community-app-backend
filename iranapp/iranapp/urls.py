from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenRefreshView

from korook_admin.spa_views import AdminSpaView
from accounts.views import ResetPasswordPageView

urlpatterns = [
    path(
        "reset-password/",
        ResetPasswordPageView.as_view(),
        name="reset-password-page",
    ),
    path('admin/', admin.site.urls),
    re_path(r'^admin-app(?:/(?P<path>.*))?$', AdminSpaView.as_view(), name='korook-admin-spa'),

    # 👇 همه‌ی URLهای listings (از جمله /listings/ و /listings/<id>/) از اینجا می‌آیند
    path('api/', include('listings.urls')),

    # لاگین/لاگ‌اوت DRF
    path('api/auth/', include('rest_framework.urls')),

    path('api/accounts/', include('accounts.urls')),

    path('api/admin/', include('korook_admin.urls')),

    path('api/', include('korook_platform.urls')),

    path(
        "api/token/refresh/",
        TokenRefreshView.as_view(),
        name="token_refresh",
    ),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
