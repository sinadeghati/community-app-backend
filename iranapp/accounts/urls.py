from django.urls import path
from .views import LoginView, PasswordResetView, ProfileView, RegisterView

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('register/', RegisterView.as_view(), name='register'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('password/reset/', PasswordResetView.as_view(), name='password-reset'),
]
