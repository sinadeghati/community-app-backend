from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.utils import timezone

from listings.models import Listing
from korook_platform.models import BusinessClaim, UserPlatformProfile


class AdminAuthTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.staff = User.objects.create_user(
            username="staff1",
            email="staff1@korook.com",
            password="StaffPass!234",
            is_staff=True,
        )
        UserPlatformProfile.objects.filter(user=self.staff).update(
            role=UserPlatformProfile.Role.ADMIN
        )

    def test_staff_login_and_dashboard(self):
        login = self.client.post(
            "/api/admin/auth/login/",
            {"username": "staff1", "password": "StaffPass!234"},
            content_type="application/json",
        )
        self.assertEqual(login.status_code, 200)
        stats = self.client.get("/api/admin/dashboard/stats/")
        self.assertEqual(stats.status_code, 200)
        self.assertIn("users_total", stats.json())
        self.assertIn("claims_pending", stats.json())

    def test_non_staff_cannot_login(self):
        User.objects.create_user(
            username="user1",
            email="user1@korook.com",
            password="UserPass!234",
        )
        login = self.client.post(
            "/api/admin/auth/login/",
            {"username": "user1", "password": "UserPass!234"},
            content_type="application/json",
        )
        self.assertEqual(login.status_code, 403)


class ClaimQueueTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.staff = User.objects.create_user(
            username="staff2",
            email="staff2@korook.com",
            password="StaffPass!234",
            is_staff=True,
        )
        self.requester = User.objects.create_user(
            username="owner1",
            email="owner1@korook.com",
            password="OwnerPass!234",
        )
        self.listing = Listing.objects.create(
            user=self.requester,
            title="Test Cafe",
            city="LA",
            state="CA",
            contact_info="test@cafe.com",
        )
        self.claim = BusinessClaim.objects.create(
            listing=self.listing,
            requester=self.requester,
        )
        self.client.post(
            "/api/admin/auth/login/",
            {"username": "staff2", "password": "StaffPass!234"},
            content_type="application/json",
        )

    def test_claim_queue_and_approve(self):
        queue = self.client.get("/api/admin/claims/")
        self.assertEqual(queue.status_code, 200)
        results = queue.json()["results"]
        self.assertEqual(len(results), 1)
        approve = self.client.post(f"/api/admin/claims/{self.claim.id}/approve/")
        self.assertEqual(approve.status_code, 200)
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.owner_id, self.requester.id)
