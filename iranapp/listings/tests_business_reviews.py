import os

from django.conf import settings
from django.contrib.auth.models import User
from django.db import connection
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import get_or_create_email_profile
from .models import BusinessReview, Listing


def _refuse_remote_database():
    database_url = os.environ.get("DATABASE_URL") or ""
    if database_url.strip():
        raise RuntimeError("Refusing review tests because DATABASE_URL is set.")
    if "korook.com" in database_url.casefold():
        raise RuntimeError("Refusing review tests aimed at api.korook.com.")

    database = settings.DATABASES["default"]
    engine = str(database.get("ENGINE", ""))
    name = str(database.get("NAME", ""))
    host = str(database.get("HOST", ""))
    if "sqlite" not in engine:
        raise RuntimeError("Refusing review tests because the database is not SQLite.")
    for marker in (name, host, database_url):
        folded = marker.casefold()
        if "korook.com" in folded or "railway" in folded:
            raise RuntimeError("Refusing review tests because the database target is remote.")


_refuse_remote_database()


class BusinessReviewApiTests(TestCase):
    def setUp(self):
        _refuse_remote_database()
        self.assertEqual(connection.vendor, "sqlite")
        self.assertNotIn("korook.com", str(connection.settings_dict).casefold())

        self.client = APIClient()
        self.password = "SecurePass123!"
        self.owner = self._user("owner")
        self.claimant = self._user("claimant")
        self.reviewer = self._user("reviewer")
        self.other = self._user("other")
        self.listing = Listing.objects.create(
            user=self.owner,
            title="Public Cafe",
            city="San Diego",
            state="CA",
            contact_info="cafe@example.com",
            status=Listing.Status.PUBLISHED,
        )
        self.draft = Listing.objects.create(
            user=self.owner,
            title="Draft Cafe",
            city="San Diego",
            state="CA",
            contact_info="draft@example.com",
            status=Listing.Status.DRAFT,
        )
        self.list_url = f"/api/listings/{self.listing.id}/reviews/"

    def _user(self, username):
        user = User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password=self.password,
        )
        get_or_create_email_profile(user).mark_verified()
        return user

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

    def _logout(self):
        self.client.credentials()

    def _create_review(self, username="reviewer", rating=5, text="Excellent food."):
        self._login(username)
        return self.client.post(
            self.list_url,
            {"rating": rating, "text": text, "status": "hidden"},
            format="json",
        )

    def test_guest_sees_empty_approved_summary(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            {
                "listing_id": self.listing.id,
                "average_rating": None,
                "review_count": 0,
                "reviews": [],
            },
        )

    def test_guest_cannot_submit_review(self):
        response = self.client.post(
            self.list_url,
            {"rating": 5, "text": "Nice."},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(BusinessReview.objects.count(), 0)

    def test_authenticated_review_is_approved_and_public(self):
        created = self._create_review()
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        self.assertEqual(created.data["status"], BusinessReview.Status.APPROVED)
        self.assertEqual(created.data["author_username"], "reviewer")
        self.assertEqual(created.data["rating"], 5)
        self.assertNotIn("email", created.data)
        self.assertNotIn("@", str(created.data))

        self._logout()
        listed = self.client.get(self.list_url)
        self.assertEqual(listed.status_code, status.HTTP_200_OK)
        self.assertEqual(listed.data["average_rating"], "5.0")
        self.assertEqual(listed.data["review_count"], 1)
        self.assertEqual(listed.data["reviews"][0]["text"], "Excellent food.")
        self.assertNotIn("email", listed.data["reviews"][0])

    def test_duplicate_review_is_rejected(self):
        first = self._create_review()
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        second = self._create_review(text="A second try.")
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(BusinessReview.objects.filter(listing=self.listing).count(), 1)

    def test_listing_user_and_owner_cannot_review(self):
        self.listing.owner = self.claimant
        self.listing.save(update_fields=["owner"])

        owner_response = self._create_review(username="owner")
        self.assertEqual(owner_response.status_code, status.HTTP_403_FORBIDDEN)
        claimant_response = self._create_review(username="claimant")
        self.assertEqual(claimant_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(BusinessReview.objects.count(), 0)

        allowed = self._create_review(username="reviewer")
        self.assertEqual(allowed.status_code, status.HTTP_201_CREATED)

    def test_unpublished_listing_is_not_reviewable(self):
        self._login("reviewer")
        response = self.client.post(
            f"/api/listings/{self.draft.id}/reviews/",
            {"rating": 4, "text": "Hidden draft."},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(BusinessReview.objects.count(), 0)
        self.assertEqual(
            self.client.get(f"/api/listings/{self.draft.id}/reviews/").status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_invalid_rating_and_blank_text_are_rejected(self):
        self._login("reviewer")
        for rating in (0, 6, 1.5):
            response = self.client.post(
                self.list_url,
                {"rating": rating, "text": "Okay"},
                format="json",
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        blank = self.client.post(
            self.list_url,
            {"rating": 4, "text": "   "},
            format="json",
        )
        self.assertEqual(blank.status_code, status.HTTP_400_BAD_REQUEST)
        too_long = self.client.post(
            self.list_url,
            {"rating": 4, "text": "a" * 2001},
            format="json",
        )
        self.assertEqual(too_long.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(BusinessReview.objects.count(), 0)

    def test_average_uses_only_approved_reviews(self):
        self.assertEqual(self._create_review(rating=5).status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            self._create_review(username="other", rating=4, text="Good.").status_code,
            status.HTTP_201_CREATED,
        )
        BusinessReview.objects.create(
            listing=self.listing,
            author=self.claimant,
            rating=1,
            text="Should not count.",
            status=BusinessReview.Status.HIDDEN,
        )
        BusinessReview.objects.create(
            listing=self.listing,
            author=self.owner,
            rating=1,
            text="Pending should not count.",
            status=BusinessReview.Status.PENDING,
        )

        self._logout()
        listed = self.client.get(self.list_url)
        self.assertEqual(listed.data["review_count"], 2)
        self.assertEqual(listed.data["average_rating"], "4.5")
        self.assertEqual(
            [item["author_username"] for item in listed.data["reviews"]],
            ["other", "reviewer"],
        )

        self._login("owner")
        author_list = self.client.get(self.list_url)
        self.assertEqual(author_list.data["review_count"], 2)
        self.assertEqual(author_list.data["average_rating"], "4.5")
        self.assertIn(
            "Pending should not count.",
            [item["text"] for item in author_list.data["reviews"]],
        )
        self._logout()

        hidden = BusinessReview.objects.get(status=BusinessReview.Status.HIDDEN)
        hidden_response = self.client.get(
            f"/api/listings/{self.listing.id}/reviews/{hidden.id}/"
        )
        self.assertEqual(hidden_response.status_code, status.HTTP_404_NOT_FOUND)

        self._login("claimant")
        author_response = self.client.get(
            f"/api/listings/{self.listing.id}/reviews/{hidden.id}/"
        )
        self.assertEqual(author_response.status_code, status.HTTP_200_OK)
        self.assertEqual(author_response.data["status"], BusinessReview.Status.HIDDEN)

    def test_three_ratings_round_half_up_to_one_decimal(self):
        self._create_review(username="reviewer", rating=5, text="A")
        self._create_review(username="other", rating=5, text="B")
        self._create_review(username="claimant", rating=4, text="C")
        self._logout()
        listed = self.client.get(self.list_url)
        self.assertEqual(listed.data["average_rating"], "4.7")
        self.assertEqual(listed.data["review_count"], 3)

    def test_author_can_edit_and_other_users_cannot(self):
        created = self._create_review(rating=5, text="Excellent food.")
        review_id = created.data["id"]
        detail_url = f"/api/listings/{self.listing.id}/reviews/{review_id}/"

        edited = self.client.patch(
            detail_url,
            {"rating": 3, "text": "  Updated text  ", "status": "hidden"},
            format="json",
        )
        self.assertEqual(edited.status_code, status.HTTP_200_OK)
        self.assertEqual(edited.data["rating"], 3)
        self.assertEqual(edited.data["text"], "Updated text")
        self.assertEqual(edited.data["status"], BusinessReview.Status.APPROVED)

        self._login("other")
        forbidden = self.client.patch(
            detail_url,
            {"rating": 1, "text": "Hijack"},
            format="json",
        )
        self.assertEqual(forbidden.status_code, status.HTTP_403_FORBIDDEN)
        review = BusinessReview.objects.get(pk=review_id)
        self.assertEqual(review.rating, 3)
        self.assertEqual(review.text, "Updated text")

    def test_author_delete_updates_average(self):
        reviewer_review = self._create_review(username="reviewer", rating=5, text="A")
        other_review = self._create_review(username="other", rating=3, text="B")
        reviewer_url = (
            f"/api/listings/{self.listing.id}/reviews/{reviewer_review.data['id']}/"
        )
        other_url = f"/api/listings/{self.listing.id}/reviews/{other_review.data['id']}/"

        forbidden = self.client.delete(reviewer_url)
        self.assertEqual(forbidden.status_code, status.HTTP_403_FORBIDDEN)

        deleted = self.client.delete(other_url)
        self.assertEqual(deleted.status_code, status.HTTP_204_NO_CONTENT)

        self._logout()
        listed = self.client.get(self.list_url)
        self.assertEqual(listed.data["review_count"], 1)
        self.assertEqual(listed.data["average_rating"], "5.0")
        self.assertEqual(listed.data["reviews"][0]["id"], reviewer_review.data["id"])

    def test_deleting_author_removes_review_from_public_average(self):
        created = self._create_review()
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        self.reviewer.delete()
        self.assertFalse(BusinessReview.objects.filter(listing=self.listing).exists())
        self._logout()
        listed = self.client.get(self.list_url)
        self.assertEqual(listed.status_code, status.HTTP_200_OK)
        self.assertEqual(listed.data["review_count"], 0)
        self.assertIsNone(listed.data["average_rating"])
