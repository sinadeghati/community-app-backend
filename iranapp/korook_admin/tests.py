from django.contrib.auth.models import User
from django.core.cache import cache
from django.db import connection
from django.test import Client, TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from listings.models import Listing, ListingImage
from korook_platform.models import BusinessClaim, UserPlatformProfile

from .dashboard_views import DASHBOARD_STATS_CACHE_KEY, build_dashboard_stats


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


class AdminDashboardStatsTests(TestCase):
    def setUp(self):
        cache.delete(DASHBOARD_STATS_CACHE_KEY)
        self.client = Client(enforce_csrf_checks=False)
        self.staff = User.objects.create_user(
            username="staff3",
            email="staff3@korook.com",
            password="StaffPass!234",
            is_staff=True,
        )
        self.client.post(
            "/api/admin/auth/login/",
            {"username": "staff3", "password": "StaffPass!234"},
            content_type="application/json",
        )
        Listing.objects.create(
            user=self.staff,
            title="Published Shop",
            city="LA",
            state="CA",
            contact_info="shop@korook.com",
            status=Listing.Status.PUBLISHED,
        )
        Listing.objects.create(
            user=self.staff,
            title="Draft Shop",
            city="SF",
            state="CA",
            contact_info="draft@korook.com",
            status=Listing.Status.DRAFT,
        )

    def test_dashboard_stats_totals(self):
        stats = build_dashboard_stats()
        self.assertGreaterEqual(stats["users_total"], 1)
        self.assertEqual(stats["businesses_total"], 2)
        self.assertEqual(stats["businesses_draft"], 1)
        self.assertEqual(stats["businesses_pending"], 1)

        response = self.client.get("/api/admin/dashboard/stats/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["businesses_total"], 2)

    def test_dashboard_stats_use_bounded_query_count(self):
        cache.delete(DASHBOARD_STATS_CACHE_KEY)
        with CaptureQueriesContext(connection) as ctx:
            build_dashboard_stats()
        self.assertLessEqual(len(ctx.captured_queries), 8)


class AdminBusinessListPerformanceTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.staff = User.objects.create_user(
            username="staff4",
            email="staff4@korook.com",
            password="StaffPass!234",
            is_staff=True,
        )
        self.client.post(
            "/api/admin/auth/login/",
            {"username": "staff4", "password": "StaffPass!234"},
            content_type="application/json",
        )
        self.listing = Listing.objects.create(
            user=self.staff,
            title="Cafe Alpha",
            business_name="Cafe Alpha",
            city="Los Angeles",
            state="CA",
            contact_info="alpha@cafe.com",
            status=Listing.Status.PUBLISHED,
            is_featured=True,
        )
        ListingImage.objects.create(
            listing=self.listing,
            image="listings/cover.jpg",
            role=ListingImage.Role.COVER,
        )
        ListingImage.objects.create(
            listing=self.listing,
            image="listings/gallery-1.jpg",
            role=ListingImage.Role.GALLERY,
        )
        ListingImage.objects.create(
            listing=self.listing,
            image="listings/gallery-2.jpg",
            role=ListingImage.Role.GALLERY,
        )

    def test_business_list_returns_lightweight_payload(self):
        response = self.client.get("/api/admin/businesses/?page_size=25")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["count"], 1)
        row = body["results"][0]
        self.assertEqual(row["title"], "Cafe Alpha")
        self.assertEqual(row["city"], "Los Angeles")
        self.assertEqual(row["status"], "published")
        self.assertTrue(row["is_featured"])
        self.assertIn("thumbnail_url", row)
        self.assertNotIn("images", row)
        self.assertIn("cover.jpg", row["thumbnail_url"])

    def test_business_list_bounded_query_count(self):
        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get("/api/admin/businesses/?page_size=25")
        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(ctx.captured_queries), 5)

    def test_business_list_search_and_status_filter(self):
        Listing.objects.create(
            user=self.staff,
            title="Hidden Shop",
            city="San Diego",
            state="CA",
            contact_info="hidden@shop.com",
            status=Listing.Status.HIDDEN,
        )
        search_response = self.client.get("/api/admin/businesses/?search=Alpha")
        self.assertEqual(search_response.json()["count"], 1)

        status_response = self.client.get("/api/admin/businesses/?status=hidden")
        self.assertEqual(status_response.json()["count"], 1)
        self.assertEqual(status_response.json()["results"][0]["title"], "Hidden Shop")

    def test_business_detail_still_returns_full_payload(self):
        response = self.client.get(f"/api/admin/businesses/{self.listing.id}/")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("images", body)
        self.assertEqual(len(body["images"]), 3)

    def test_business_list_city_filter(self):
        Listing.objects.create(
            user=self.staff,
            title="SD Shop",
            city="San Diego",
            state="CA",
            contact_info="sd@shop.com",
            status=Listing.Status.PUBLISHED,
        )
        response = self.client.get("/api/admin/businesses/?city=San Diego")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(response.json()["results"][0]["title"], "SD Shop")


class AdminBusinessCrudTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.staff = User.objects.create_user(
            username="staff5",
            email="staff5@korook.com",
            password="StaffPass!234",
            is_staff=True,
        )
        self.owner = User.objects.create_user(
            username="owner5",
            email="owner5@korook.com",
            password="OwnerPass!234",
        )
        self.client.post(
            "/api/admin/auth/login/",
            {"username": "staff5", "password": "StaffPass!234"},
            content_type="application/json",
        )
        self.listing = Listing.objects.create(
            user=self.owner,
            owner=self.owner,
            title="Original Title",
            business_name="Original Title",
            city="Los Angeles",
            state="CA",
            contact_info="original@shop.com",
            status=Listing.Status.DRAFT,
        )

    def test_create_business(self):
        response = self.client.post(
            "/api/admin/businesses/",
            {
                "title": "New Shop",
                "business_name": "New Shop",
                "city": "Irvine",
                "state": "CA",
                "contact_info": "new@shop.com",
                "category": "Restaurant",
                "owner_id": self.owner.id,
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["title"], "New Shop")
        self.assertEqual(body["owner_id"], self.owner.id)

    def test_create_business_requires_owner(self):
        response = self.client.post(
            "/api/admin/businesses/",
            {
                "title": "No Owner Shop",
                "city": "Irvine",
                "state": "CA",
                "contact_info": "noowner@shop.com",
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("owner_id", response.json()["detail"].lower())

    def test_patch_business(self):
        response = self.client.patch(
            f"/api/admin/businesses/{self.listing.id}/",
            {
                "title": "Updated Title",
                "description": "Updated description",
                "phone": "555-0100",
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["title"], "Updated Title")
        self.assertEqual(body["description"], "Updated description")
        self.assertEqual(body["phone"], "555-0100")

    def test_publish_and_hide_actions(self):
        publish = self.client.post(f"/api/admin/businesses/{self.listing.id}/publish/")
        self.assertEqual(publish.status_code, 200)
        self.assertEqual(publish.json()["status"], Listing.Status.PUBLISHED)

        hide = self.client.post(f"/api/admin/businesses/{self.listing.id}/hide/")
        self.assertEqual(hide.status_code, 200)
        self.assertEqual(hide.json()["status"], Listing.Status.HIDDEN)

    def test_feature_and_verify_actions(self):
        feature = self.client.post(
            f"/api/admin/businesses/{self.listing.id}/feature/",
            {"is_featured": True},
            content_type="application/json",
        )
        self.assertEqual(feature.status_code, 200)
        self.assertTrue(feature.json()["is_featured"])

        unfeature = self.client.post(
            f"/api/admin/businesses/{self.listing.id}/feature/",
            {"is_featured": False},
            content_type="application/json",
        )
        self.assertEqual(unfeature.status_code, 200)
        self.assertFalse(unfeature.json()["is_featured"])

        verify = self.client.post(
            f"/api/admin/businesses/{self.listing.id}/verify/",
            {"verified_badge": True},
            content_type="application/json",
        )
        self.assertEqual(verify.status_code, 200)
        self.assertTrue(verify.json()["verified_badge"])
        self.assertIsNotNone(verify.json()["verified_at"])

    def test_delete_business(self):
        listing_id = self.listing.id
        response = self.client.delete(f"/api/admin/businesses/{listing_id}/")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Listing.objects.filter(pk=listing_id).exists())
