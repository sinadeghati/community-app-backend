from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('admin/', admin.site.urls),

    # 👇 همه‌ی URLهای listings (از جمله /listings/ و /listings/<id>/) از اینجا می‌آیند
    path('api/', include('listings.urls')),

    # لاگین/لاگ‌اوت DRF
    path('api/auth/', include('rest_framework.urls')),

    path('api/accounts/', include('accounts.urls')),

    path(
        "api/token/refresh/",
        TokenRefreshView.as_view(),
        name="token_refresh",
    ),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
