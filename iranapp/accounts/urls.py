from django.urls import path
from .social_views import (
    AppleAuthView,
    AppleLinkView,
    GoogleAuthView,
    GoogleLinkView,
    ProviderDisconnectView,
    SocialLoginMethodsView,
)
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
    path('auth/google/', GoogleAuthView.as_view(), name='auth-google'),
    path('auth/apple/', AppleAuthView.as_view(), name='auth-apple'),
    path('auth/google/link/', GoogleLinkView.as_view(), name='auth-google-link'),
    path('auth/apple/link/', AppleLinkView.as_view(), name='auth-apple-link'),
    path(
        'auth/<str:provider>/disconnect/',
        ProviderDisconnectView.as_view(),
        name='auth-provider-disconnect',
    ),
    path('auth/methods/', SocialLoginMethodsView.as_view(), name='auth-methods'),
]
