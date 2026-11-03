import os

from django.conf import settings
from django.contrib.auth.models import User
from django.db import connection
from django.test import Client, TestCase

from accounts.models import get_or_create_email_profile
from korook_platform.models import AdminAuditLog, ContentReport
from listings.models import BusinessReview, Listing


def _refuse_remote_database():
    database_url = os.environ.get("DATABASE_URL") or ""
    if database_url.strip():
        raise RuntimeError("Refusing admin review tests because DATABASE_URL is set.")
    if "korook.com" in database_url.casefold():
        raise RuntimeError("Refusing admin review tests aimed at api.korook.com.")
    database = settings.DATABASES["default"]
    if "sqlite" not in str(database.get("ENGINE", "")):
        raise RuntimeError("Refusing admin review tests because the database is not SQLite.")
    for marker in (str(database.get("NAME", "")), str(database.get("HOST", "")), database_url):
        if "korook.com" in marker.casefold() or "railway" in marker.casefold():
            raise RuntimeError("Refusing admin review tests because the database target is remote.")


_refuse_remote_database()


class AdminReviewQueueTests(TestCase):
    def setUp(self):
        _refuse_remote_database()
        self.assertEqual(connection.vendor, "sqlite")
        self.client = Client(enforce_csrf_checks=False)
        self.password = "StaffPass!234"
        self.staff = User.objects.create_user(
            username="review_staff",
            email="review_staff@example.com",
            password=self.password,
            is_staff=True,
        )
        self.member = User.objects.create_user(
            username="review_member",
            email="review_member@example.com",
            password=self.password,
        )
        self.author = User.objects.create_user(
            username="queue_author",
            email="queue_author@example.com",
            password=self.password,
        )
        self.reporter = User.objects.create_user(
            username="queue_reporter",
            email="queue_reporter@example.com",
            password=self.password,
        )
        for user in (self.staff, self.member, self.author, self.reporter):
            get_or_create_email_profile(user).mark_verified()
        self.listing = Listing.objects.create(
            user=self.staff,
            title="Queue Listing",
            business_name="Queue Cafe",
            city="San Diego",
            state="CA",
            contact_info="queue@example.com",
            status=Listing.Status.PUBLISHED,
        )
        self.pending = self._review(BusinessReview.Status.PENDING, "Held for staff.", 2)
        self.published = self._review(BusinessReview.Status.APPROVED, "Public praise.", 5)
        self.hidden = self._review(BusinessReview.Status.HIDDEN, "Hidden text.", 1)
        self.removed = self._review(BusinessReview.Status.REMOVED, "Removed text.", 1)
        ContentReport.objects.create(
            reported_object_type=ContentReport.ObjectType.REVIEW,
            reported_object_id=self.published.id,
            business_review=self.published,
            listing=self.listing,
            reported_user=self.author,
            reported_by=self.reporter,
            reason="spam_or_scam",
            description="Copied advertisement.",
        )

    def _review(self, status, text, rating):
        author = User.objects.create_user(
            username=f"author_{status}_{rating}_{text[:4]}",
            email=f"{status}.{rating}.{User.objects.count()}@example.com",
            password=self.password,
        )
        get_or_create_email_profile(author).mark_verified()
        return BusinessReview.objects.create(
            listing=self.listing,
            author=author,
            rating=rating,
            text=text,
            status=status,
        )

    def _staff_login(self):
        response = self.client.post(
            "/api/admin/auth/login/",
            {"username": "review_staff", "password": self.password},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

    def test_non_staff_cannot_view_or_moderate_the_queue(self):
        anonymous = self.client.get("/api/admin/reviews/")
        self.assertEqual(anonymous.status_code, 403)
        self.client.force_login(self.member)
        forbidden = self.client.post(f"/api/admin/reviews/{self.pending.id}/approve/")
        self.assertEqual(forbidden.status_code, 403)
        self.pending.refresh_from_db()
        self.assertEqual(self.pending.status, BusinessReview.Status.PENDING)

    def test_queue_lists_moderation_fields_and_filters(self):
        self._staff_login()
        listed = self.client.get("/api/admin/reviews/?page_size=25")
        self.assertEqual(listed.status_code, 200)
        row = next(item for item in listed.json()["results"] if item["id"] == self.published.id)
        self.assertEqual(row["business_name"], "Queue Cafe")
        self.assertEqual(row["rating"], 5)
        self.assertEqual(row["text"], "Public praise.")
        self.assertEqual(row["status"], "approved")
        self.assertEqual(row["report_count"], 1)
        self.assertIn("created_at", row)
        self.assertNotIn("@", row["author_username"])

        pending = self.client.get("/api/admin/reviews/?status=pending")
        self.assertEqual([item["id"] for item in pending.json()["results"]], [self.pending.id])
        published = self.client.get("/api/admin/reviews/?status=approved")
        self.assertEqual([item["id"] for item in published.json()["results"]], [self.published.id])
        hidden = self.client.get("/api/admin/reviews/?status=hidden")
        self.assertEqual([item["id"] for item in hidden.json()["results"]], [self.hidden.id])
        removed = self.client.get("/api/admin/reviews/?status=removed")
        self.assertEqual([item["id"] for item in removed.json()["results"]], [self.removed.id])
        reported = self.client.get("/api/admin/reviews/?status=reported")
        self.assertEqual([item["id"] for item in reported.json()["results"]], [self.published.id])

        reports = self.client.get(
            f"/api/admin/reports/?object_type=review&object_id={self.published.id}"
        )
        self.assertEqual(reports.status_code, 200)
        self.assertEqual(reports.json()["results"][0]["reason"], "spam_or_scam")
        self.assertEqual(reports.json()["results"][0]["description"], "Copied advertisement.")

    def test_staff_actions_are_audited_and_change_public_visibility(self):
        self._staff_login()
        approved = self.client.post(f"/api/admin/reviews/{self.pending.id}/approve/")
        self.assertEqual(approved.status_code, 200)
        self.assertEqual(approved.json()["status"], "approved")
        self.assertTrue(
            AdminAuditLog.objects.filter(
                action_type="review.approve",
                object_type="business_review",
                object_id=self.pending.id,
                actor=self.staff,
            ).exists()
        )

        hidden = self.client.post(f"/api/admin/reviews/{self.published.id}/hide/")
        self.assertEqual(hidden.status_code, 200)
        self.assertEqual(hidden.json()["status"], "hidden")
        removed = self.client.post(f"/api/admin/reviews/{self.published.id}/remove/")
        self.assertEqual(removed.status_code, 200)
        self.assertEqual(removed.json()["status"], "removed")
        restored = self.client.post(f"/api/admin/reviews/{self.published.id}/restore/")
        self.assertEqual(restored.status_code, 200)
        self.assertEqual(restored.json()["status"], "approved")

        self.listing.refresh_from_db()
        self.assertEqual(self.listing.status, Listing.Status.PUBLISHED)
        public = self.client.get(f"/api/listings/{self.listing.id}/reviews/")
        self.assertEqual(public.status_code, 200)
        public_ids = {item["id"] for item in public.json()["reviews"]}
        self.assertIn(self.pending.id, public_ids)
        self.assertIn(self.published.id, public_ids)
        self.assertNotIn(self.hidden.id, public_ids)
        self.assertNotIn(self.removed.id, public_ids)
