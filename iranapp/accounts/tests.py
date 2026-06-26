from unittest.mock import patch

from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.test import TestCase
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.test import APIClient

from listings.models import Listing

from .models import UserEmailProfile, get_or_create_email_profile, is_user_email_verified
from .tokens import email_verification_token_generator
from .verification_codes import issue_verification_code


class LoginViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.password = "SecurePass123!"
        self.user = User.objects.create_user(
            username="alice",
            email="alice@example.com",
            password=self.password,
        )
        get_or_create_email_profile(self.user).mark_verified()
        self.login_url = "/api/accounts/login/"

    def test_login_with_username(self):
        response = self.client.post(
            self.login_url,
            {"username": "alice", "password": self.password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_login_with_email_field(self):
        response = self.client.post(
            self.login_url,
            {"email": "alice@example.com", "password": self.password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_login_with_email_in_username_field(self):
        response = self.client.post(
            self.login_url,
            {"username": "alice@example.com", "password": self.password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_login_wrong_password(self):
        response = self.client.post(
            self.login_url,
            {"username": "alice", "password": "wrong-password"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["detail"], "Invalid username or password."
        )

    def test_register_then_login_with_email(self):
        register_url = "/api/accounts/register/"
        payload = {
            "username": "bob",
            "email": "bob@example.com",
            "password": self.password,
        }
        with patch("accounts.views.send_email_verification") as mock_send:
            mock_send.return_value = "123456"
            register_response = self.client.post(
                register_url, payload, format="json"
            )
        self.assertEqual(register_response.status_code, status.HTTP_201_CREATED)

        login_response = self.client.post(
            self.login_url,
            {"email": "bob@example.com", "password": self.password},
            format="json",
        )
        self.assertEqual(login_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("verify your email", login_response.data["detail"].lower())

        bob = User.objects.get(username="bob")
        profile = get_or_create_email_profile(bob)
        code = issue_verification_code(profile)
        verify_response = self.client.post(
            "/api/accounts/email/verify/",
            {"email": "bob@example.com", "code": code},
            format="json",
        )
        self.assertEqual(verify_response.status_code, status.HTTP_200_OK)
        self.assertIn("access", verify_response.data)

        login_response = self.client.post(
            self.login_url,
            {"email": "bob@example.com", "password": self.password},
            format="json",
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        self.assertIn("access", login_response.data)


class RegisterValidationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.password = "SecurePass123!"
        self.register_url = "/api/accounts/register/"
        User.objects.create_user(
            username="existing",
            email="existing@example.com",
            password=self.password,
        )

    @patch("accounts.views.send_email_verification")
    def test_register_rejects_duplicate_username(self, mock_send):
        response = self.client.post(
            self.register_url,
            {
                "username": "existing",
                "email": "new@example.com",
                "password": self.password,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("username", response.data)
        mock_send.assert_not_called()

    @patch("accounts.views.send_email_verification")
    def test_register_rejects_duplicate_username_case_insensitive(self, mock_send):
        response = self.client.post(
            self.register_url,
            {
                "username": "EXISTING",
                "email": "new@example.com",
                "password": self.password,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("username", response.data)
        mock_send.assert_not_called()

    @patch("accounts.views.send_email_verification")
    def test_register_rejects_duplicate_email(self, mock_send):
        response = self.client.post(
            self.register_url,
            {
                "username": "newuser",
                "email": "existing@example.com",
                "password": self.password,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)
        mock_send.assert_not_called()

    @patch("accounts.views.send_email_verification")
    def test_register_normalizes_username_and_email(self, mock_send):
        response = self.client.post(
            self.register_url,
            {
                "username": "NewUser",
                "email": "NewUser@Example.COM",
                "password": self.password,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username="newuser")
        self.assertEqual(user.email, "newuser@example.com")
        mock_send.assert_called_once()


class PasswordResetRequestViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.password = "SecurePass123!"
        self.user = User.objects.create_user(
            username="alice",
            email="alice@example.com",
            password=self.password,
        )
        self.reset_url = "/api/accounts/password/reset/"

    @patch("accounts.views.send_password_reset_email")
    def test_password_reset_request_sends_email(self, mock_send):
        response = self.client.post(
            self.reset_url,
            {"email": "alice@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        mock_send.assert_called_once_with(self.user)

    @patch("accounts.views.send_password_reset_email")
    def test_password_reset_request_unknown_email_same_response(self, mock_send):
        response = self.client.post(
            self.reset_url,
            {"email": "missing@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        mock_send.assert_not_called()


class PasswordResetConfirmViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.password = "SecurePass123!"
        self.new_password = "NewSecurePass456!"
        self.user = User.objects.create_user(
            username="alice",
            email="alice@example.com",
            password=self.password,
        )
        self.confirm_url = "/api/accounts/password/reset/confirm/"
        self.uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        self.token = default_token_generator.make_token(self.user)

    def test_confirm_resets_password(self):
        response = self.client.post(
            self.confirm_url,
            {
                "uid": self.uid,
                "token": self.token,
                "new_password": self.new_password,
                "confirm_password": self.new_password,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.new_password))

    def test_confirm_then_login_with_new_password(self):
        get_or_create_email_profile(self.user).mark_verified()
        self.client.post(
            self.confirm_url,
            {
                "uid": self.uid,
                "token": self.token,
                "new_password": self.new_password,
                "confirm_password": self.new_password,
            },
            format="json",
        )
        login_response = self.client.post(
            "/api/accounts/login/",
            {"email": "alice@example.com", "password": self.new_password},
            format="json",
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        self.assertIn("access", login_response.data)

    def test_confirm_rejects_invalid_token(self):
        response = self.client.post(
            self.confirm_url,
            {
                "uid": self.uid,
                "token": "invalid-token",
                "new_password": self.new_password,
                "confirm_password": self.new_password,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("token", response.data)

    def test_confirm_rejects_password_mismatch(self):
        response = self.client.post(
            self.confirm_url,
            {
                "uid": self.uid,
                "token": self.token,
                "new_password": self.new_password,
                "confirm_password": "DifferentPass789!",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("confirm_password", response.data)


class EmailVerificationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.password = "SecurePass123!"
        self.user = User.objects.create_user(
            username="carol",
            email="carol@example.com",
            password=self.password,
        )
        get_or_create_email_profile(self.user)
        self.verify_url = "/api/accounts/email/verify/"
        self.resend_url = "/api/accounts/email/resend-verification/"
        self.uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        self.token = email_verification_token_generator.make_token(self.user)

    def test_verify_email_with_code_returns_tokens(self):
        code = issue_verification_code(self.user.email_profile)
        response = self.client.post(
            self.verify_url,
            {"email": "carol@example.com", "code": code},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.user.email_profile.refresh_from_db()
        self.assertTrue(self.user.email_profile.email_verified)

    def test_resend_mobile_alias_path(self):
        with patch("accounts.views.send_email_verification") as mock_send:
            response = self.client.post(
                "/api/accounts/email/resend/",
                {"email": "carol@example.com"},
                format="json",
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_send.assert_called_once()

    def test_verify_email_success(self):
        response = self.client.post(
            self.verify_url,
            {"uid": self.uid, "token": self.token},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.user.email_profile.refresh_from_db()
        self.assertTrue(self.user.email_profile.email_verified)

    def test_verify_rejects_invalid_token(self):
        response = self.client.post(
            self.verify_url,
            {"uid": self.uid, "token": "invalid-token"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("token", response.data)

    @patch("accounts.views.send_email_verification")
    def test_register_sends_verification_email(self, mock_send):
        response = self.client.post(
            "/api/accounts/register/",
            {
                "username": "dave",
                "email": "dave@example.com",
                "password": self.password,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mock_send.assert_called_once()

    @patch("accounts.views.send_email_verification")
    def test_resend_verification_for_unverified_user(self, mock_send):
        response = self.client.post(
            self.resend_url,
            {"email": "carol@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        mock_send.assert_called_once()

    @patch("accounts.views.send_email_verification")
    def test_resend_verification_skips_verified_user(self, mock_send):
        profile = get_or_create_email_profile(self.user)
        profile.mark_verified()

        response = self.client.post(
            self.resend_url,
            {"email": "carol@example.com"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_send.assert_not_called()


class DeleteAccountViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.password = "SecurePass123!"
        self.user = User.objects.create_user(
            username="erin",
            email="erin@example.com",
            password=self.password,
        )
        get_or_create_email_profile(self.user).mark_verified()
        self.delete_url = "/api/accounts/delete-account/"

        login_response = self.client.post(
            "/api/accounts/login/",
            {"email": "erin@example.com", "password": self.password},
            format="json",
        )
        self.access = login_response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access}")

        self.listing = Listing.objects.create(
            user=self.user,
            title="Erin's Shop",
            city="Los Angeles",
            state="CA",
            contact_info="erin@example.com",
        )

    def test_delete_account_removes_user_and_profile(self):
        user_id = self.user.id

        response = self.client.delete(self.delete_url, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertFalse(User.objects.filter(pk=user_id).exists())
        self.assertFalse(UserEmailProfile.objects.filter(user_id=user_id).exists())

    def test_delete_account_removes_owned_listings(self):
        listing_id = self.listing.id

        response = self.client.delete(self.delete_url, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Listing.objects.filter(pk=listing_id).exists())

    def test_login_fails_after_account_deleted(self):
        self.client.delete(self.delete_url, format="json")
        self.client.credentials()

        login_response = self.client.post(
            "/api/accounts/login/",
            {"email": "erin@example.com", "password": self.password},
            format="json",
        )

        self.assertEqual(login_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_account_mobile_alias_path(self):
        user_id = self.user.id
        response = self.client.delete("/api/accounts/delete/", format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(User.objects.filter(pk=user_id).exists())

    def test_delete_account_requires_authentication(self):
        self.client.credentials()

        response = self.client.delete(self.delete_url, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
