from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from .models import ExternalIdentity, get_or_create_email_profile
from .provider_verification import ProviderTokenError, VerifiedProviderIdentity
from .social_auth_service import (
    SocialAuthError,
    disconnect_provider,
    link_provider_to_user,
    login_or_register_with_provider,
)


def _google_identity(
    subject="google-sub-1",
    email="newuser@example.com",
    email_verified=True,
):
    return VerifiedProviderIdentity(
        provider=ExternalIdentity.Provider.GOOGLE,
        subject=subject,
        email=email,
        email_verified=email_verified,
        given_name="New",
        family_name="User",
    )


def _apple_identity(
    subject="apple-sub-1",
    email="hide@privaterelay.appleid.com",
    email_verified=True,
):
    return VerifiedProviderIdentity(
        provider=ExternalIdentity.Provider.APPLE,
        subject=subject,
        email=email,
        email_verified=email_verified,
    )


@override_settings(
    SOCIAL_AUTH_GOOGLE_CLIENT_IDS="staging-google-client.apps.googleusercontent.com",
    SOCIAL_AUTH_APPLE_CLIENT_IDS="com.korook.app",
)
class SocialAuthViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.google_url = "/api/accounts/auth/google/"
        self.apple_url = "/api/accounts/auth/apple/"

    @patch("accounts.social_views.verify_google_id_token")
    def test_google_login_issues_jwt(self, mock_verify):
        mock_verify.return_value = _google_identity()
        response = self.client.post(
            self.google_url, {"id_token": "valid-token"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertTrue(response.data["created"])
        self.assertEqual(ExternalIdentity.objects.count(), 1)

    @patch("accounts.social_views.verify_google_id_token")
    def test_google_login_repeat_same_subject(self, mock_verify):
        mock_verify.return_value = _google_identity()
        first = self.client.post(self.google_url, {"id_token": "t1"}, format="json")
        second = self.client.post(self.google_url, {"id_token": "t2"}, format="json")
        self.assertEqual(first.data["user_id"], second.data["user_id"])
        self.assertFalse(second.data["created"])
        self.assertEqual(User.objects.count(), 1)

    @patch("accounts.social_views.verify_google_id_token")
    def test_existing_verified_email_requires_link(self, mock_verify):
        user = User.objects.create_user(
            username="alice",
            email="alice@example.com",
            password="SecurePass123!",
        )
        get_or_create_email_profile(user).mark_verified()
        mock_verify.return_value = _google_identity(
            subject="other-sub", email="alice@example.com"
        )
        response = self.client.post(self.google_url, {"id_token": "x"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data["code"], "existing_account_link_required")
        self.assertEqual(User.objects.count(), 1)

    @patch("accounts.social_views.verify_google_id_token")
    def test_invalid_token_from_verifier(self, mock_verify):
        mock_verify.side_effect = ProviderTokenError("bad sig", code="invalid_token")
        response = self.client.post(self.google_url, {"id_token": "x"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["code"], "invalid_token")

    @patch("accounts.social_views.verify_apple_identity_token")
    def test_apple_hide_my_email_creates_user(self, mock_verify):
        mock_verify.return_value = _apple_identity()
        response = self.client.post(
            self.apple_url,
            {"identity_token": "apple-token", "nonce": "n1"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user = User.objects.get(pk=response.data["user_id"])
        self.assertTrue(user.email_profile.email_verified)

    def test_concurrent_first_login_single_user(self):
        identity = _google_identity(subject="race-sub")
        user_a, created_a, _ = login_or_register_with_provider(identity)
        user_b, created_b, _ = login_or_register_with_provider(identity)
        self.assertTrue(created_a)
        self.assertFalse(created_b)
        self.assertEqual(user_a.pk, user_b.pk)
        self.assertEqual(
            ExternalIdentity.objects.filter(provider_subject="race-sub").count(), 1
        )

    @patch("accounts.social_views.verify_google_id_token")
    def test_authenticated_link(self, mock_verify):
        user = User.objects.create_user(
            username="linker",
            email="linker@example.com",
            password="SecurePass123!",
        )
        get_or_create_email_profile(user).mark_verified()
        self.client.force_authenticate(user=user)
        mock_verify.return_value = _google_identity(
            subject="link-sub", email="linker@example.com"
        )
        response = self.client.post(
            "/api/accounts/auth/google/link/",
            {"id_token": "link"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("google", response.data["login_methods"]["providers"])

    @patch("accounts.social_views.verify_google_id_token")
    def test_disconnect_last_method_rejected(self, mock_verify):
        mock_verify.return_value = _google_identity(subject="only-google")
        login = self.client.post(self.google_url, {"id_token": "only"}, format="json")
        user = User.objects.get(pk=login.data["user_id"])
        self.client.force_authenticate(user=user)
        response = self.client.delete("/api/accounts/auth/google/disconnect/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["code"], "cannot_disconnect_last_method")

    def test_disconnect_with_password_allowed(self):
        user = User.objects.create_user(
            username="pwuser",
            email="pwuser@example.com",
            password="SecurePass123!",
        )
        get_or_create_email_profile(user).mark_verified()
        ExternalIdentity.objects.create(
            user=user,
            provider=ExternalIdentity.Provider.GOOGLE,
            provider_subject="g-sub",
            provider_email="pwuser@example.com",
        )
        self.client.force_authenticate(user=user)
        response = self.client.delete("/api/accounts/auth/google/disconnect/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch("accounts.social_views.verify_google_id_token")
    def test_failure_does_not_create_partial_user(self, mock_verify):
        mock_verify.side_effect = ProviderTokenError("expired", code="token_expired")
        before = User.objects.count()
        response = self.client.post(self.google_url, {"id_token": "bad"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(User.objects.count(), before)

    def test_provider_subject_unique_constraint(self):
        u1 = User.objects.create_user(username="u1", email="u1@x.com", password="x")
        u2 = User.objects.create_user(username="u2", email="u2@x.com", password="x")
        ExternalIdentity.objects.create(
            user=u1,
            provider=ExternalIdentity.Provider.GOOGLE,
            provider_subject="dup",
        )
        with self.assertRaises(Exception):
            ExternalIdentity.objects.create(
                user=u2,
                provider=ExternalIdentity.Provider.GOOGLE,
                provider_subject="dup",
            )


class SocialAuthServiceTests(TestCase):
    def test_link_after_password_login(self):
        user = User.objects.create_user(
            username="bob",
            email="bob@example.com",
            password="SecurePass123!",
        )
        get_or_create_email_profile(user).mark_verified()
        link_provider_to_user(user, _google_identity(subject="bob-google", email="bob@example.com"))
        self.assertEqual(user.external_identities.count(), 1)

    def test_disconnect_service(self):
        user = User.objects.create_user(
            username="d1", email="d1@x.com", password="SecurePass123!"
        )
        get_or_create_email_profile(user).mark_verified()
        ExternalIdentity.objects.create(
            user=user,
            provider=ExternalIdentity.Provider.APPLE,
            provider_subject="a1",
        )
        disconnect_provider(user, ExternalIdentity.Provider.APPLE)
        self.assertEqual(user.external_identities.count(), 0)
