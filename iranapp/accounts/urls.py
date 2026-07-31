from django.urls import path
from .views import (
    ChangePasswordView,
    DeleteAccountView,
    EmailVerifyView,
    LoginView,
    PasswordResetConfirmView,
    PasswordResetView,
    ProfileView,
    RegisterView,
    ResendVerificationView,
)

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('register/', RegisterView.as_view(), name='register'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('email/verify/', EmailVerifyView.as_view(), name='email-verify'),
    path(
        'email/resend-verification/',
        ResendVerificationView.as_view(),
        name='email-resend-verification',
    ),
    path('email/resend/', ResendVerificationView.as_view(), name='email-resend'),
    path(
        'password/reset/confirm/',
        PasswordResetConfirmView.as_view(),
        name='password-reset-confirm',
    ),
    path('password/reset/', PasswordResetView.as_view(), name='password-reset'),
    path('password/change/', ChangePasswordView.as_view(), name='password-change'),
    path('delete-account/', DeleteAccountView.as_view(), name='delete-account'),
    path('delete/', DeleteAccountView.as_view(), name='delete'),
]
