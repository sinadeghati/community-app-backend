from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from .models import Listing


class MyListingOwnershipTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.password = "SecurePass123!"
        self.user_a = User.objects.create_user(
            username="user_a",
            email="user_a@example.com",
            password=self.password,
        )
        self.user_b = User.objects.create_user(
            username="user_b",
            email="user_b@example.com",
            password=self.password,
        )
        self.listing_a = Listing.objects.create(
            user=self.user_a,
            title="User A Business",
            city="LA",
            state="CA",
        )
        self.listing_b = Listing.objects.create(
            user=self.user_b,
            title="User B Business",
            city="SD",
            state="CA",
        )
        self.my_listing_url = "/api/my-listing/"

    def _login(self, username):
        response = self.client.post(
            "/api/accounts/login/",
            {"username": username, "password": self.password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {response.data['access']}"
        )

    def test_user_a_sees_only_own_listings(self):
        self._login("user_a")
        response = self.client.get(self.my_listing_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = [item["title"] for item in response.data]
        self.assertEqual(titles, ["User A Business"])

    def test_user_b_sees_only_own_listings(self):
        self._login("user_b")
        response = self.client.get(self.my_listing_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = [item["title"] for item in response.data]
        self.assertEqual(titles, ["User B Business"])

    def test_user_b_cannot_update_user_a_listing(self):
        self._login("user_b")
        response = self.client.patch(
            f"/api/listings/{self.listing_a.id}/",
            {"title": "Hijacked"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.listing_a.refresh_from_db()
        self.assertEqual(self.listing_a.title, "User A Business")
