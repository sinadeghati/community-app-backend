from django.contrib.auth.models import User
from django.contrib.auth import authenticate

from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated

from rest_framework_simplejwt.tokens import RefreshToken

from .password_reset import send_password_reset_email
from .serializers import PasswordResetRequestSerializer, RegisterSerializer


# ========== REGISTER API ==========
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]


# ========== LOGIN API ==========
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")

        if not username or not password:
            return Response(
                {"detail": "Username and password are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = authenticate(username=username, password=password)

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
            send_password_reset_email(user)

        return Response(self.SUCCESS_RESPONSE)


# ========== PROFILE API ==========
class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response(
            {
                "username": user.username,
                "email": user.email,
            }
        )
