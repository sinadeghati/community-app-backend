from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import get_or_create_email_profile
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
        get_or_create_email_profile(self.user_a).mark_verified()
        get_or_create_email_profile(self.user_b).mark_verified()
        self.listing_a = Listing.objects.create(
            user=self.user_a,
            title="User A Business",
            city="LA",
            state="CA",
            contact_info="a@example.com",
        )
        self.listing_b = Listing.objects.create(
            user=self.user_b,
            title="User B Business",
            city="SD",
            state="CA",
            contact_info="b@example.com",
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

    def test_authenticated_user_can_create_listing(self):
        self._login("user_a")
        response = self.client.post(
            "/api/listings/",
            {
                "title": "New Business",
                "city": "LA",
                "state": "CA",
                "contact_info": "new@example.com",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["title"], "New Business")

    def test_authenticated_user_can_edit_own_listing(self):
        self._login("user_a")
        response = self.client.patch(
            f"/api/my-listing/{self.listing_a.id}/",
            {"description": "Updated description"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.listing_a.refresh_from_db()
        self.assertEqual(self.listing_a.description, "Updated description")


class ListingCategoriesTests(TestCase):
    def test_categories_endpoint_returns_canonical_list(self):
        response = APIClient().get("/api/listings/categories/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        values = [item["value"] for item in response.data]
        self.assertIn("Food", values)
        self.assertIn("Real Estate", values)
        self.assertEqual(values[0], "Food")
