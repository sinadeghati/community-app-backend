import os

from django.conf import settings
from django.contrib.auth.models import User
from django.db import connection
from django.test import Client, TestCase
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import UserBlock, get_or_create_email_profile
from listings.models import BusinessReview, Listing


def _refuse_remote_database():
    database_url = os.environ.get("DATABASE_URL") or ""
    if database_url.strip():
        raise RuntimeError("Refusing review safety tests because DATABASE_URL is set.")
    if "korook.com" in database_url.casefold():
        raise RuntimeError("Refusing review safety tests aimed at api.korook.com.")
    database = settings.DATABASES["default"]
    engine = str(database.get("ENGINE", ""))
    name = str(database.get("NAME", ""))
    host = str(database.get("HOST", ""))
    if "sqlite" not in engine:
        raise RuntimeError("Refusing review safety tests because the database is not SQLite.")
    for marker in (name, host, database_url):
        folded = marker.casefold()
        if "korook.com" in folded or "railway" in folded:
            raise RuntimeError("Refusing review safety tests because the database target is remote.")


_refuse_remote_database()


class ReviewBlockVisibilityTests(TestCase):
    def setUp(self):
        _refuse_remote_database()
        self.assertEqual(connection.vendor, "sqlite")
        self.client = APIClient()
        self.password = "SecurePass123!"
        self.owner = self._user("owner")
        self.reviewer = self._user("reviewer")
        self.other = self._user("other")
        self.viewer = self._user("viewer")
        self.listing = Listing.objects.create(
            user=self.owner,
            title="Block Cafe",
            city="San Diego",
            state="CA",
            contact_info="cafe@example.com",
            status=Listing.Status.PUBLISHED,
        )
        self.reviewer_review = BusinessReview.objects.create(
            listing=self.listing,
            author=self.reviewer,
            rating=5,
            text="Great food.",
            status=BusinessReview.Status.APPROVED,
        )
        self.other_review = BusinessReview.objects.create(
            listing=self.listing,
            author=self.other,
            rating=3,
            text="Good service.",
            status=BusinessReview.Status.APPROVED,
        )
        self.list_url = f"/api/listings/{self.listing.id}/reviews/"
        self.detail_url = (
            f"/api/listings/{self.listing.id}/reviews/{self.reviewer_review.id}/"
        )

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
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def _summary(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return response.data

    def test_block_and_unblock_permissions(self):
        guest = self.client.post(
            "/api/accounts/blocks/",
            {"user_id": self.reviewer.id},
            format="json",
        )
        self.assertEqual(guest.status_code, status.HTTP_401_UNAUTHORIZED)

        self._login("viewer")
        self_block = self.client.post(
            "/api/accounts/blocks/",
            {"user_id": self.viewer.id},
            format="json",
        )
        self.assertEqual(self_block.status_code, status.HTTP_400_BAD_REQUEST)

        missing = self.client.post(
            "/api/accounts/blocks/",
            {"user_id": 999999},
            format="json",
        )
        self.assertEqual(missing.status_code, status.HTTP_404_NOT_FOUND)

        created = self.client.post(
            "/api/accounts/blocks/",
            {"user_id": self.reviewer.id},
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        self.assertEqual(created.data["username"], "reviewer")
        self.assertNotIn("email", created.data)

        duplicate = self.client.post(
            "/api/accounts/blocks/",
            {"user_id": self.reviewer.id},
            format="json",
        )
        self.assertEqual(duplicate.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(UserBlock.objects.count(), 1)

        listed = self.client.get("/api/accounts/blocks/")
        self.assertEqual(listed.status_code, status.HTTP_200_OK)
        self.assertEqual([row["id"] for row in listed.data["blocked_users"]], [self.reviewer.id])
        self.assertNotIn("email", listed.data["blocked_users"][0])

        self._login("other")
        foreign = self.client.delete(f"/api/accounts/blocks/{self.reviewer.id}/")
        self.assertEqual(foreign.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(UserBlock.objects.count(), 1)
        other_list = self.client.get("/api/accounts/blocks/")
        self.assertEqual(other_list.data["blocked_users"], [])

        self._login("viewer")
        removed = self.client.delete(f"/api/accounts/blocks/{self.reviewer.id}/")
        self.assertEqual(removed.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(UserBlock.objects.count(), 0)

    def test_blocked_author_reviews_are_hidden_only_from_the_blocker(self):
        self._login("viewer")
        blocked = self.client.post(
            "/api/accounts/blocks/",
            {"user_id": self.reviewer.id},
            format="json",
        )
        self.assertEqual(blocked.status_code, status.HTTP_201_CREATED)

        visible = self._summary()
        self.assertEqual(visible["review_count"], 1)
        self.assertEqual(visible["average_rating"], "3.0")
        self.assertEqual(visible["reviews"][0]["id"], self.other_review.id)
        detail = self.client.get(self.detail_url)
        self.assertEqual(detail.status_code, status.HTTP_404_NOT_FOUND)
        report = self.client.post(
            f"{self.detail_url}report/",
            {"reason": "spam_or_scam"},
            format="json",
        )
        self.assertEqual(report.status_code, status.HTTP_404_NOT_FOUND)

        self.client.credentials()
        guest = self._summary()
        self.assertEqual(guest["review_count"], 2)
        self.assertEqual(guest["average_rating"], "4.0")

        self._login("other")
        other_view = self._summary()
        self.assertEqual(other_view["review_count"], 2)
        self.assertEqual(other_view["average_rating"], "4.0")

        self._login("viewer")
        self.client.delete(f"/api/accounts/blocks/{self.reviewer.id}/")
        restored = self._summary()
        self.assertEqual(restored["review_count"], 2)
        self.assertEqual(restored["average_rating"], "4.0")
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.status, Listing.Status.PUBLISHED)


class ReviewContentFilterTests(TestCase):
    def setUp(self):
        _refuse_remote_database()
        self.assertEqual(connection.vendor, "sqlite")
        self.client = APIClient()
        self.admin = Client(enforce_csrf_checks=False)
        self.password = "SecurePass123!"
        self.owner = self._user("owner")
        self.author = self._user("author")
        self.reader = self._user("reader")
        self.staff = User.objects.create_user(
            username="staff_filter",
            email="staff_filter@example.com",
            password=self.password,
            is_staff=True,
        )
        get_or_create_email_profile(self.staff).mark_verified()
        self.listing = Listing.objects.create(
            user=self.owner,
            title="Filter Cafe",
            city="San Diego",
            state="CA",
            contact_info="cafe@example.com",
            status=Listing.Status.PUBLISHED,
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
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def _post(self, username, text, rating=4):
        self._login(username)
        return self.client.post(
            self.list_url,
            {"rating": rating, "text": text},
            format="json",
        )

    def test_prohibited_categories_are_held_and_clean_text_stays_public(self):
        clean = self._post("author", "The spice blend and cocktail were excellent.")
        self.assertEqual(clean.status_code, status.HTTP_201_CREATED)
        self.assertEqual(clean.data["status"], BusinessReview.Status.APPROVED)
        self.assertNotIn("moderation_notice", clean.data)

        held = {
            "profanity": "This place is fucking dirty.",
            "harassment": "Just kill yourself.",
            "hate": "They used a slur: nigger.",
            "spam": "Click here for free money.",
            "prohibited": "Message me to buy cocaine.",
            "leet": "What the f*ck was that.",
            "links": "See https://one.example and https://two.example now.",
        }
        for index, (category, text) in enumerate(held.items(), start=1):
            user = self._user(f"held{index}")
            response = self._post(user.username, text)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED, category)
            self.assertEqual(response.data["status"], BusinessReview.Status.PENDING, category)
            self.assertIn("moderation", response.data["moderation_notice"].casefold())

        self.client.credentials()
        public = self.client.get(self.list_url)
        self.assertEqual(public.status_code, status.HTTP_200_OK)
        self.assertEqual(public.data["review_count"], 1)
        self.assertEqual(public.data["average_rating"], "4.0")
        self.assertEqual(public.data["reviews"][0]["text"], clean.data["text"])
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.status, Listing.Status.PUBLISHED)
        self.assertEqual(Listing.objects.count(), 1)

    def test_author_can_correct_held_text_and_bad_edits_leave_public_view(self):
        created = self._post("author", "This place is fucking dirty.")
        self.assertEqual(created.data["status"], BusinessReview.Status.PENDING)
        detail_url = f"/api/listings/{self.listing.id}/reviews/{created.data['id']}/"

        author_view = self.client.get(detail_url)
        self.assertEqual(author_view.status_code, status.HTTP_200_OK)
        self.assertEqual(author_view.data["status"], BusinessReview.Status.PENDING)

        cleaned = self.client.patch(
            detail_url,
            {"text": "The meal was much better than expected."},
            format="json",
        )
        self.assertEqual(cleaned.status_code, status.HTTP_200_OK)
        self.assertEqual(cleaned.data["status"], BusinessReview.Status.APPROVED)
        self.assertNotIn("moderation_notice", cleaned.data)

        self.client.credentials()
        public = self.client.get(self.list_url)
        self.assertEqual(public.data["review_count"], 1)

        self._login("author")
        dirtied = self.client.patch(
            detail_url,
            {"text": "This is shit."},
            format="json",
        )
        self.assertEqual(dirtied.data["status"], BusinessReview.Status.PENDING)
        self.client.credentials()
        public = self.client.get(self.list_url)
        self.assertEqual(public.data["review_count"], 0)
        self.assertIsNone(public.data["average_rating"])

    def test_hidden_review_stays_hidden_when_the_author_edits_it(self):
        created = self._post("author", "Excellent food.")
        review = BusinessReview.objects.get(pk=created.data["id"])
        review.status = BusinessReview.Status.HIDDEN
        review.save(update_fields=["status", "updated_at"])

        edited = self.client.patch(
            f"/api/listings/{self.listing.id}/reviews/{review.id}/",
            {"text": "A perfectly clean update."},
            format="json",
        )
        self.assertEqual(edited.status_code, status.HTTP_200_OK)
        self.assertEqual(edited.data["status"], BusinessReview.Status.HIDDEN)
        self.client.credentials()
        public = self.client.get(self.list_url)
        self.assertEqual(public.data["review_count"], 0)

    def test_staff_can_restore_a_held_review_to_public(self):
        created = self._post("author", "Click here for free money.")
        review_id = created.data["id"]
        login = self.admin.post(
            "/api/admin/auth/login/",
            {"username": "staff_filter", "password": self.password},
            content_type="application/json",
        )
        self.assertEqual(login.status_code, status.HTTP_200_OK)
        restored = self.admin.post(f"/api/admin/reviews/{review_id}/restore/")
        self.assertEqual(restored.status_code, status.HTTP_200_OK)
        self.assertEqual(restored.json()["status"], BusinessReview.Status.APPROVED)

        self.client.credentials()
        public = self.client.get(self.list_url)
        self.assertEqual(public.data["review_count"], 1)
        self.assertEqual(public.data["reviews"][0]["id"], review_id)
