from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.test import TestCase
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.test import APIClient


class LoginViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.password = "SecurePass123!"
        self.user = User.objects.create_user(
            username="alice",
            email="alice@example.com",
            password=self.password,
        )
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
        register_response = self.client.post(
            register_url, payload, format="json"
        )
        self.assertEqual(register_response.status_code, status.HTTP_201_CREATED)

        login_response = self.client.post(
            self.login_url,
            {"email": "bob@example.com", "password": self.password},
            format="json",
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        self.assertIn("access", login_response.data)


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
