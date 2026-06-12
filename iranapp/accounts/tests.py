from django.contrib.auth.models import User
from django.test import TestCase
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
