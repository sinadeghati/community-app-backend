from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import get_or_create_email_profile
from listings.models import Listing

from .models import ContentReport, Event


class PublicEventListViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(
            username="event_owner",
            email="event_owner@example.com",
            password="SecurePass123!",
        )
        Event.objects.create(
            owner=self.owner,
            title="Community Meetup",
            description="A published event",
            category="Community",
            starts_at=timezone.now(),
            status=Event.Status.PUBLISHED,
        )
        Event.objects.create(
            owner=self.owner,
            title="Draft Event",
            starts_at=timezone.now(),
            status=Event.Status.DRAFT,
        )

    def test_public_events_list_returns_published_only(self):
        response = self.client.get("/api/events/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "Community Meetup")
        self.assertEqual(response.data[0]["business_category"], "Community")
        self.assertEqual(response.data[0]["about"], "A published event")


class UserContentReportCreateViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.password = "SecurePass123!"
        self.reporter = User.objects.create_user(
            username="reporter_user",
            email="reporter@example.com",
            password=self.password,
        )
        self.reported_user = User.objects.create_user(
            username="reported_user",
            email="reported@example.com",
            password=self.password,
        )
        get_or_create_email_profile(self.reporter).mark_verified()
        get_or_create_email_profile(self.reported_user).mark_verified()
        self.listing = Listing.objects.create(
            user=self.reported_user,
            owner=self.reported_user,
            title="Reported Business",
            city="San Diego",
            state="CA",
            contact_info="reported@example.com",
        )
        self.event = Event.objects.create(
            owner=self.reported_user,
            title="Reported Event",
            starts_at=timezone.now(),
            status=Event.Status.PUBLISHED,
        )
        self.staff = User.objects.create_user(
            username="staff_admin",
            email="staff@example.com",
            password=self.password,
            is_staff=True,
        )
        self.report_url = "/api/reports/"

    def _auth_as_reporter(self):
        login = self.client.post(
            "/api/accounts/login/",
            {"username": "reporter_user", "password": self.password},
            format="json",
        )
        self.assertEqual(login.status_code, status.HTTP_200_OK)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    def test_authenticated_user_can_submit_listing_report(self):
        self._auth_as_reporter()
        response = self.client.post(
            self.report_url,
            {
                "target_type": "business",
                "target_id": self.listing.id,
                "reason": "spam_or_scam",
                "description": "Looks fraudulent",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        body = response.json()
        self.assertEqual(body["target_type"], "listing")
        self.assertEqual(body["target_id"], self.listing.id)
        self.assertEqual(body["reason"], "spam_or_scam")
        self.assertEqual(body["status"], "new")
        self.assertIn("id", body)
        self.assertIn("created_at", body)

        report = ContentReport.objects.get(pk=body["id"])
        self.assertEqual(report.reported_by_id, self.reporter.id)
        self.assertEqual(report.listing_id, self.listing.id)
        self.assertEqual(report.reported_user_id, self.reported_user.id)
        self.assertNotIn("admin_note", body)

    def test_unauthenticated_report_is_rejected(self):
        response = self.client.post(
            self.report_url,
            {
                "target_type": "listing",
                "target_id": self.listing.id,
                "reason": "other",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_invalid_target_is_rejected(self):
        self._auth_as_reporter()
        response = self.client.post(
            self.report_url,
            {
                "target_type": "listing",
                "target_id": 999999,
                "reason": "other",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("target_id", response.json())

    def test_invalid_reason_is_rejected(self):
        self._auth_as_reporter()
        response = self.client.post(
            self.report_url,
            {
                "target_type": "listing",
                "target_id": self.listing.id,
                "reason": "not_a_real_reason",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("reason", response.json())

    def test_child_safety_report(self):
        self._auth_as_reporter()
        response = self.client.post(
            self.report_url,
            {
                "target_type": "user",
                "target_id": self.reported_user.id,
                "reason": "child_safety",
                "description": "Concern about profile content",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        report = ContentReport.objects.get(pk=response.json()["id"])
        self.assertEqual(report.reason, "child_safety")
        self.assertEqual(report.reported_object_type, ContentReport.ObjectType.USER)
        self.assertEqual(report.reported_user_id, self.reported_user.id)

    def test_submitted_report_appears_in_admin_list(self):
        self._auth_as_reporter()
        create = self.client.post(
            self.report_url,
            {
                "target_type": "event",
                "target_id": self.event.id,
                "reason": "harassment_or_abuse",
            },
            format="json",
        )
        self.assertEqual(create.status_code, status.HTTP_201_CREATED)
        report_id = create.json()["id"]

        admin_client = Client(enforce_csrf_checks=False)
        login = admin_client.post(
            "/api/admin/auth/login/",
            {"username": "staff_admin", "password": self.password},
            content_type="application/json",
        )
        self.assertEqual(login.status_code, status.HTTP_200_OK)

        admin_list = admin_client.get("/api/admin/reports/?status=new")
        self.assertEqual(admin_list.status_code, status.HTTP_200_OK)
        ids = [row["id"] for row in admin_list.json()["results"]]
        self.assertIn(report_id, ids)

        admin_detail = admin_client.get(f"/api/admin/reports/{report_id}/")
        self.assertEqual(admin_detail.status_code, status.HTTP_200_OK)
        self.assertEqual(admin_detail.json()["reason"], "harassment_or_abuse")
        self.assertEqual(admin_detail.json()["reported_object_type"], "event")
        self.assertEqual(admin_detail.json()["status"], "new")
