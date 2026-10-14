import logging

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ExternalIdentity
from .provider_verification import (
    ProviderTokenError,
    verify_apple_identity_token,
    verify_google_id_token,
)
from .social_auth_service import (
    SocialAuthError,
    disconnect_provider,
    issue_jwt_pair,
    link_provider_to_user,
    login_or_register_with_provider,
    user_login_methods,
)

logger = logging.getLogger(__name__)


def _provider_error_response(exc: ProviderTokenError) -> Response:
    return Response(
        {"detail": str(exc), "code": exc.code},
        status=status.HTTP_400_BAD_REQUEST,
    )


def _social_error_response(exc: SocialAuthError) -> Response:
    return Response(
        {"detail": str(exc), "code": exc.code},
        status=exc.status_code,
    )


class GoogleAuthView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        id_token = (request.data.get("id_token") or request.data.get("idToken") or "").strip()
        if not id_token:
            return Response(
                {"detail": "id_token is required.", "code": "missing_token"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            identity = verify_google_id_token(id_token)
            user, created, tokens = login_or_register_with_provider(identity)
        except ProviderTokenError as exc:
            return _provider_error_response(exc)
        except SocialAuthError as exc:
            return _social_error_response(exc)

        return Response(
            {
                **tokens,
                "user_id": user.pk,
                "created": created,
                "provider": ExternalIdentity.Provider.GOOGLE,
            },
            status=status.HTTP_200_OK,
        )


class AppleAuthView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        identity_token = (
            request.data.get("identity_token")
            or request.data.get("identityToken")
            or ""
        ).strip()
        nonce = (request.data.get("nonce") or "").strip() or None
        full_name = request.data.get("full_name") or request.data.get("fullName")

        if not identity_token:
            return Response(
                {"detail": "identity_token is required.", "code": "missing_token"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            identity = verify_apple_identity_token(identity_token, nonce=nonce)
            user, created, tokens = login_or_register_with_provider(
                identity, apple_full_name=full_name if isinstance(full_name, dict) else None
            )
        except ProviderTokenError as exc:
            return _provider_error_response(exc)
        except SocialAuthError as exc:
            return _social_error_response(exc)

        return Response(
            {
                **tokens,
                "user_id": user.pk,
                "created": created,
                "provider": ExternalIdentity.Provider.APPLE,
            },
            status=status.HTTP_200_OK,
        )


class GoogleLinkView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        id_token = (request.data.get("id_token") or request.data.get("idToken") or "").strip()
        if not id_token:
            return Response(
                {"detail": "id_token is required.", "code": "missing_token"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            identity = verify_google_id_token(id_token)
            link_provider_to_user(request.user, identity)
        except ProviderTokenError as exc:
            return _provider_error_response(exc)
        except SocialAuthError as exc:
            return _social_error_response(exc)

        return Response(
            {"detail": "Google account linked.", "login_methods": user_login_methods(request.user)},
            status=status.HTTP_200_OK,
        )


class AppleLinkView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        identity_token = (
            request.data.get("identity_token")
            or request.data.get("identityToken")
            or ""
        ).strip()
        nonce = (request.data.get("nonce") or "").strip() or None
        if not identity_token:
            return Response(
                {"detail": "identity_token is required.", "code": "missing_token"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            identity = verify_apple_identity_token(identity_token, nonce=nonce)
            link_provider_to_user(request.user, identity)
        except ProviderTokenError as exc:
            return _provider_error_response(exc)
        except SocialAuthError as exc:
            return _social_error_response(exc)

        return Response(
            {"detail": "Apple account linked.", "login_methods": user_login_methods(request.user)},
            status=status.HTTP_200_OK,
        )


class ProviderDisconnectView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, provider: str):
        provider = (provider or "").strip().lower()
        try:
            disconnect_provider(request.user, provider)
        except SocialAuthError as exc:
            return _social_error_response(exc)

        return Response(
            {"detail": f"{provider} disconnected.", "login_methods": user_login_methods(request.user)},
            status=status.HTTP_200_OK,
        )


class SocialLoginMethodsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(user_login_methods(request.user))
