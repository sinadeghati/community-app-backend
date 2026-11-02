import os

from django.conf import settings
from django.contrib.auth.models import User
from django.db import connection
from django.test import Client, TestCase
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import get_or_create_email_profile
from korook_platform.models import AdminAuditLog, ContentReport
from listings.models import BusinessReview, Listing


def _refuse_remote_database():
    database_url = os.environ.get("DATABASE_URL") or ""
    if database_url.strip():
        raise RuntimeError("Refusing review moderation tests because DATABASE_URL is set.")
    if "korook.com" in database_url.casefold():
        raise RuntimeError("Refusing review moderation tests aimed at api.korook.com.")
    database = settings.DATABASES["default"]
    engine = str(database.get("ENGINE", ""))
    name = str(database.get("NAME", ""))
    host = str(database.get("HOST", ""))
    if "sqlite" not in engine:
        raise RuntimeError("Refusing review moderation tests because the database is not SQLite.")
    for marker in (name, host, database_url):
        folded = marker.casefold()
        if "korook.com" in folded or "railway" in folded:
            raise RuntimeError("Refusing review moderation tests because the database target is remote.")


_refuse_remote_database()


class ReviewReportingAndModerationTests(TestCase):
    def setUp(self):
        _refuse_remote_database()
        self.assertEqual(connection.vendor, "sqlite")
        self.client = APIClient()
        self.admin = Client(enforce_csrf_checks=False)
        self.password = "SecurePass123!"
        self.owner = self._user("owner")
        self.reviewer = self._user("reviewer")
        self.reporter = self._user("reporter")
        self.other = self._user("other")
        self.staff = User.objects.create_user(
            username="staff_review",
            email="staff_review@example.com",
            password=self.password,
            is_staff=True,
        )
        get_or_create_email_profile(self.staff).mark_verified()
        self.listing = Listing.objects.create(
            user=self.owner,
            title="Moderation Cafe",
            city="San Diego",
            state="CA",
            contact_info="cafe@example.com",
            status=Listing.Status.PUBLISHED,
        )
        self.review = BusinessReview.objects.create(
            listing=self.listing,
            author=self.reviewer,
            rating=1,
            text="This should be moderated.",
            status=BusinessReview.Status.APPROVED,
        )
        self.good_review = BusinessReview.objects.create(
            listing=self.listing,
            author=self.other,
            rating=5,
            text="Excellent.",
            status=BusinessReview.Status.APPROVED,
        )
        self.report_url = (
            f"/api/listings/{self.listing.id}/reviews/{self.review.id}/report/"
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

    def _staff_login(self):
        response = self.admin.post(
            "/api/admin/auth/login/",
            {"username": "staff_review", "password": self.password},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def _public_summary(self):
        self.client.credentials()
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return response.data

    def test_authenticated_user_can_report_with_reason_and_details(self):
        self._login("reporter")
        response = self.client.post(
            self.report_url,
            {"reason": "harassment_or_abuse", "details": "Personal attack."},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["target_type"], "review")
        self.assertEqual(response.data["target_id"], self.review.id)
        self.assertEqual(response.data["reason"], "harassment_or_abuse")
        self.assertEqual(response.data["status"], ContentReport.Status.NEW)
        self.assertNotIn("email", response.data)

        report = ContentReport.objects.get(pk=response.data["id"])
        self.assertEqual(report.reported_by_id, self.reporter.id)
        self.assertEqual(report.reported_user_id, self.reviewer.id)
        self.assertEqual(report.business_review_id, self.review.id)
        self.assertEqual(report.description, "Personal attack.")
        self.assertEqual(report.reported_object_type, ContentReport.ObjectType.REVIEW)

    def test_details_are_optional_and_invalid_reports_are_rejected(self):
        self._login("reporter")
        missing_reason = self.client.post(self.report_url, {}, format="json")
        self.assertEqual(missing_reason.status_code, status.HTTP_400_BAD_REQUEST)

        invalid_reason = self.client.post(
            self.report_url,
            {"reason": "not_a_real_reason", "details": "nope"},
            format="json",
        )
        self.assertEqual(invalid_reason.status_code, status.HTTP_400_BAD_REQUEST)

        created = self.client.post(
            self.report_url,
            {"reason": "spam_or_scam"},
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ContentReport.objects.get(pk=created.data["id"]).description, "")

        duplicate = self.client.post(
            self.report_url,
            {"reason": "other", "details": "Again."},
            format="json",
        )
        self.assertEqual(duplicate.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(ContentReport.objects.count(), 1)

    def test_guests_and_authors_cannot_report(self):
        guest = self.client.post(
            self.report_url,
            {"reason": "spam_or_scam"},
            format="json",
        )
        self.assertEqual(guest.status_code, status.HTTP_401_UNAUTHORIZED)

        self._login("reviewer")
        own = self.client.post(
            self.report_url,
            {"reason": "other", "details": "Mine."},
            format="json",
        )
        self.assertEqual(own.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(ContentReport.objects.count(), 0)

    def test_hidden_review_cannot_be_reported(self):
        self.review.status = BusinessReview.Status.HIDDEN
        self.review.save(update_fields=["status", "updated_at"])
        self._login("reporter")
        response = self.client.post(
            self.report_url,
            {"reason": "other"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(ContentReport.objects.count(), 0)

    def test_non_staff_cannot_moderate_reviews(self):
        anonymous = self.admin.post(f"/api/admin/reviews/{self.review.id}/hide/")
        self.assertEqual(anonymous.status_code, status.HTTP_403_FORBIDDEN)

        self.admin.force_login(self.reporter)
        forbidden = self.admin.post(f"/api/admin/reviews/{self.review.id}/remove/")
        self.assertEqual(forbidden.status_code, status.HTTP_403_FORBIDDEN)
        self.review.refresh_from_db()
        self.assertEqual(self.review.status, BusinessReview.Status.APPROVED)

    def test_staff_can_hide_remove_and_restore_without_changing_the_listing(self):
        self._login("reporter")
        created = self.client.post(
            self.report_url,
            {"reason": "hate_or_discrimination", "details": "Slur."},
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        self._staff_login()

        hidden = self.admin.post(f"/api/admin/reviews/{self.review.id}/hide/")
        self.assertEqual(hidden.status_code, status.HTTP_200_OK)
        self.assertEqual(hidden.json()["status"], BusinessReview.Status.HIDDEN)
        self.assertEqual(hidden.json()["author_username"], "reviewer")
        self.assertNotIn("email", hidden.json())
        self.review.refresh_from_db()
        self.listing.refresh_from_db()
        self.assertEqual(self.review.status, BusinessReview.Status.HIDDEN)
        self.assertEqual(self.listing.status, Listing.Status.PUBLISHED)
        summary = self._public_summary()
        self.assertEqual(summary["review_count"], 1)
        self.assertEqual(summary["average_rating"], "5.0")
        self.assertEqual(summary["reviews"][0]["id"], self.good_review.id)

        report = ContentReport.objects.get(pk=created.data["id"])
        report.refresh_from_db()
        self.assertEqual(report.status, ContentReport.Status.ACTIONED)
        self.assertEqual(report.action_taken, ContentReport.ActionTaken.HIDE)

        removed = self.admin.post(f"/api/admin/reviews/{self.good_review.id}/remove/")
        self.assertEqual(removed.status_code, status.HTTP_200_OK)
        self.good_review.refresh_from_db()
        self.assertEqual(self.good_review.status, BusinessReview.Status.REMOVED)
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.status, Listing.Status.PUBLISHED)
        summary = self._public_summary()
        self.assertEqual(summary["review_count"], 0)
        self.assertIsNone(summary["average_rating"])

        restored = self.admin.post(f"/api/admin/reviews/{self.good_review.id}/restore/")
        self.assertEqual(restored.status_code, status.HTTP_200_OK)
        self.good_review.refresh_from_db()
        self.assertEqual(self.good_review.status, BusinessReview.Status.APPROVED)
        summary = self._public_summary()
        self.assertEqual(summary["review_count"], 1)
        self.assertEqual(summary["average_rating"], "5.0")
        self.assertTrue(
            AdminAuditLog.objects.filter(
                action_type="review.restore",
                object_id=self.good_review.id,
            ).exists()
        )

    def test_report_queue_actions_moderate_the_review_only(self):
        self._login("reporter")
        created = self.client.post(
            "/api/reports/",
            {
                "target_type": "review",
                "target_id": self.review.id,
                "reason": "spam_or_scam",
                "description": "Copied advertisement.",
            },
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        report_id = created.data["id"]
        self._staff_login()

        hidden = self.admin.post(f"/api/admin/reports/{report_id}/hide-content/")
        self.assertEqual(hidden.status_code, status.HTTP_200_OK)
        self.review.refresh_from_db()
        self.listing.refresh_from_db()
        self.assertEqual(self.review.status, BusinessReview.Status.HIDDEN)
        self.assertEqual(self.listing.status, Listing.Status.PUBLISHED)

        removed = self.admin.post(f"/api/admin/reports/{report_id}/delete-content/")
        self.assertEqual(removed.status_code, status.HTTP_200_OK)
        self.review.refresh_from_db()
        self.assertEqual(self.review.status, BusinessReview.Status.REMOVED)
        self.assertTrue(BusinessReview.objects.filter(pk=self.review.id).exists())

        restored = self.admin.post(f"/api/admin/reports/{report_id}/restore-content/")
        self.assertEqual(restored.status_code, status.HTTP_200_OK)
        self.review.refresh_from_db()
        self.assertEqual(self.review.status, BusinessReview.Status.APPROVED)
        summary = self._public_summary()
        self.assertEqual(summary["review_count"], 2)
        self.assertEqual(summary["average_rating"], "3.0")

    def test_staff_review_list_includes_hidden_reviews(self):
        self.review.status = BusinessReview.Status.HIDDEN
        self.review.save(update_fields=["status", "updated_at"])
        self._staff_login()
        listed = self.admin.get("/api/admin/reviews/?status=hidden")
        self.assertEqual(listed.status_code, status.HTTP_200_OK)
        ids = [row["id"] for row in listed.json()["results"]]
        self.assertEqual(ids, [self.review.id])
        self.assertNotIn("@", listed.json()["results"][0]["author_username"])
