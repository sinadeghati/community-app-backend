from django.urls import path
from .views import (
    ChangePasswordView,
    LoginView,
    PasswordResetConfirmView,
    PasswordResetView,
    ProfileView,
    RegisterView,
)

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('register/', RegisterView.as_view(), name='register'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path(
        'password/reset/confirm/',
        PasswordResetConfirmView.as_view(),
        name='password-reset-confirm',
    ),
    path('password/reset/', PasswordResetView.as_view(), name='password-reset'),
    path('password/change/', ChangePasswordView.as_view(), name='password-change'),
]
