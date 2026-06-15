from django.contrib.auth.models import User
from django.contrib.auth import authenticate

from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated

from rest_framework_simplejwt.tokens import RefreshToken

from .password_reset import SendGridEmailError, send_password_reset_email
from .serializers import (
    ChangePasswordSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
)


# ========== REGISTER API ==========
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]


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
            }
        )
