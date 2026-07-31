from django.contrib.auth.models import User
from django.contrib.auth import authenticate

import logging

from django.views.generic import TemplateView

from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated

from rest_framework_simplejwt.tokens import RefreshToken

from .account_deletion import delete_user_account
from .email_verification import send_email_verification
from .models import get_or_create_email_profile, is_user_email_verified
from .password_reset import SendGridEmailError, send_password_reset_email
from .verification_codes import VerificationRateLimitError
from .serializers import (
    ChangePasswordSerializer,
    EmailVerificationRequestSerializer,
    EmailVerifySerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
)


logger = logging.getLogger(__name__)


# ========== REGISTER API ==========
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        user = serializer.save()
        get_or_create_email_profile(user)
        try:
            send_email_verification(user)
        except SendGridEmailError:
            logger.exception(
                "Failed to send verification email after registration for user pk=%s",
                user.pk,
            )
        except Exception:
            logger.exception(
                "Unexpected error sending verification email after registration for user pk=%s",
                user.pk,
            )


# ========== LOGIN API ==========
class LoginView(APIView):
    """
    Authenticate with username or email plus password.

    Accepts either:
      - {"username": "...", "password": "..."}
      - {"email": "...", "password": "..."}
    Email may also be sent in the username field for backward compatibility.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        password = request.data.get("password")
        identifier = (
            request.data.get("username") or request.data.get("email") or ""
        ).strip()

        if not identifier or not password:
            return Response(
                {"detail": "Username or email and password are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = authenticate(username=identifier, password=password)
        if user is None and "@" in identifier:
            matched = User.objects.filter(email__iexact=identifier).first()
            if matched is not None:
                user = authenticate(
                    username=matched.username, password=password
                )

        if user is None:
            return Response(
                {"detail": "Invalid username or password."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from korook_platform.models import UserPlatformProfile

        platform_profile = getattr(user, "platform_profile", None)
        if platform_profile and platform_profile.account_status in (
            UserPlatformProfile.AccountStatus.SUSPENDED,
            UserPlatformProfile.AccountStatus.DELETED,
        ):
            return Response(
                {"detail": "This account has been suspended."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not is_user_email_verified(user):
            return Response(
                {
                    "detail": (
                        "Please verify your email before signing in. "
                        "Check your inbox for a verification code."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            }
        )


# ========== PASSWORD RESET REQUEST API ==========
class PasswordResetView(APIView):
    """
    Request a password reset email. Always returns the same success response
    whether or not the email is registered (prevents account enumeration).
    """
    permission_classes = [AllowAny]

    SUCCESS_RESPONSE = {
        "success": True,
        "message": "If an account exists for this email, reset instructions have been sent.",
    }

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data["email"]
        user = User.objects.filter(email__iexact=email).first()
        if user is not None:
            try:
                send_password_reset_email(user)
            except SendGridEmailError as exc:
                return Response(
                    {"success": False, "message": str(exc)},
                    status=status.HTTP_502_BAD_GATEWAY,
                )

        return Response(self.SUCCESS_RESPONSE)


# ========== PASSWORD RESET CONFIRM API ==========
class PasswordResetConfirmView(APIView):
    """Validate uid/token from the reset email and set a new password."""

    permission_classes = [AllowAny]
    http_method_names = ["post"]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()

        return Response(
            {
                "success": True,
                "message": "Password reset successfully.",
            },
            status=status.HTTP_200_OK,
        )


class ResetPasswordPageView(TemplateView):
    """Minimal public page for staging password reset (uid/token from email link)."""

    template_name = "accounts/reset_password.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["uid"] = self.request.GET.get("uid", "")
        context["token"] = self.request.GET.get("token", "")
        context["confirm_api_path"] = "/api/accounts/password/reset/confirm/"
        return context


# ========== EMAIL VERIFICATION API ==========
class EmailVerifyView(APIView):
    """Validate uid/token from the verification email."""

    permission_classes = [AllowAny]
    http_method_names = ["post"]

    def post(self, request):
        serializer = EmailVerifySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            profile = serializer.save()
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = profile.user
        if profile.email_verified:
            refresh = RefreshToken.for_user(user)
            return Response(
                {
                    "success": True,
                    "message": "Email verified successfully.",
                    "email_verified": True,
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {
                "success": False,
                "message": "Email could not be verified.",
                "email_verified": False,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )


class ResendVerificationView(APIView):
    """
    Resend email verification link. Always returns the same success response
    whether or not the email is registered (prevents account enumeration).
    """

    permission_classes = [AllowAny]
    http_method_names = ["post"]

    SUCCESS_RESPONSE = {
        "success": True,
        "message": (
            "If an account exists for this email and is not yet verified, "
            "verification instructions have been sent."
        ),
    }

    def post(self, request):
        serializer = EmailVerificationRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data["email"]
        user = User.objects.filter(email__iexact=email).first()
        if user is not None and not is_user_email_verified(user):
            try:
                send_email_verification(user)
            except VerificationRateLimitError as exc:
                headers = {}
                if exc.retry_after_seconds is not None:
                    headers["Retry-After"] = str(exc.retry_after_seconds)
                return Response(
                    {"success": False, "message": str(exc)},
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                    headers=headers,
                )
            except SendGridEmailError as exc:
                return Response(
                    {"success": False, "message": str(exc)},
                    status=status.HTTP_502_BAD_GATEWAY,
                )

        return Response(self.SUCCESS_RESPONSE)


# ========== CHANGE PASSWORD API ==========
class ChangePasswordView(APIView):
    """Change password for the authenticated user."""

    permission_classes = [IsAuthenticated]
    http_method_names = ["post"]

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={"request": request},
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()

        return Response(
            {
                "success": True,
                "message": "Password updated successfully",
            },
            status=status.HTTP_200_OK,
        )


# ========== PROFILE API ==========
class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "email_verified": is_user_email_verified(user),
            }
        )


# ========== DELETE ACCOUNT API ==========
class DeleteAccountView(APIView):
    """Permanently delete the authenticated user and related owned data."""

    permission_classes = [IsAuthenticated]
    http_method_names = ["delete"]

    def delete(self, request):
        refresh_token = None
        if isinstance(request.data, dict):
            refresh_token = request.data.get("refresh")

        user = request.user
        delete_user_account(user, refresh_token=refresh_token)

        return Response(
            {
                "success": True,
                "message": "Account deleted successfully.",
            },
            status=status.HTTP_200_OK,
        )
