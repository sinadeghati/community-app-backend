from django.contrib.auth.models import User
from django.core.cache import cache
from django.db import connection
from django.test import Client, TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from listings.models import Listing, ListingImage
from korook_platform.models import BusinessClaim, Event, UserPlatformProfile

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


class AdminUserManagementTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.staff = User.objects.create_user(
            username="staff6",
            email="staff6@korook.com",
            password="StaffPass!234",
            is_staff=True,
        )
        self.target = User.objects.create_user(
            username="target_user",
            email="target@korook.com",
            password="TargetPass!234",
            first_name="Target",
            last_name="User",
        )
        self.superuser = User.objects.create_user(
            username="protected_admin",
            email="protected@korook.com",
            password="AdminPass!234",
            is_staff=True,
            is_superuser=True,
        )
        self.client.post(
            "/api/admin/auth/login/",
            {"username": "staff6", "password": "StaffPass!234"},
            content_type="application/json",
        )
        Listing.objects.create(
            user=self.target,
            owner=self.target,
            title="Target Cafe",
            city="LA",
            state="CA",
            contact_info="target@korook.com",
            status=Listing.Status.PUBLISHED,
        )
        Event.objects.create(
            title="Target Event",
            owner=self.target,
            starts_at=timezone.now(),
            city="LA",
            state="CA",
            status=Event.Status.PUBLISHED,
        )
        BusinessClaim.objects.create(
            listing=Listing.objects.get(user=self.target),
            requester=self.target,
        )

    def test_user_list_search_and_filters(self):
        response = self.client.get("/api/admin/users/?search=target")
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(response.json()["count"], 1)

        suspended_filter = self.client.get("/api/admin/users/?account_status=active")
        self.assertEqual(suspended_filter.status_code, 200)

        verified_filter = self.client.get("/api/admin/users/?email_verified=false")
        self.assertEqual(verified_filter.status_code, 200)

    def test_user_list_includes_summary_fields(self):
        response = self.client.get("/api/admin/users/?search=target_user")
        self.assertEqual(response.status_code, 200)
        row = response.json()["results"][0]
        self.assertEqual(row["username"], "target_user")
        self.assertEqual(row["display_name"], "Target User")
        self.assertIn("businesses_count", row)
        self.assertNotIn("password", row)

    def test_user_detail_get(self):
        response = self.client.get(f"/api/admin/users/{self.target.id}/")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["email"], "target@korook.com")
        self.assertGreaterEqual(body["businesses_count"], 1)
        self.assertGreaterEqual(body["events_count"], 1)
        self.assertGreaterEqual(body["claims_count"], 1)

    def test_user_businesses_endpoint_is_lightweight(self):
        response = self.client.get(f"/api/admin/users/{self.target.id}/businesses/")
        self.assertEqual(response.status_code, 200)
        row = response.json()["results"][0]
        self.assertIn("title", row)
        self.assertNotIn("images", row)

    def test_user_claims_endpoint(self):
        response = self.client.get(f"/api/admin/users/{self.target.id}/claims/")
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(response.json()["count"], 1)

    def test_suspend_and_unsuspend_user(self):
        suspend = self.client.post(f"/api/admin/users/{self.target.id}/suspend/")
        self.assertEqual(suspend.status_code, 200)
        self.assertEqual(suspend.json()["account_status"], "suspended")
        self.target.refresh_from_db()
        self.assertFalse(self.target.is_active)

        unsuspend = self.client.post(f"/api/admin/users/{self.target.id}/unsuspend/")
        self.assertEqual(unsuspend.status_code, 200)
        self.assertEqual(unsuspend.json()["account_status"], "active")
        self.target.refresh_from_db()
        self.assertTrue(self.target.is_active)

    def test_cannot_suspend_staff_or_self(self):
        self_response = self.client.post(f"/api/admin/users/{self.staff.id}/suspend/")
        self.assertEqual(self_response.status_code, 403)

        protected = self.client.post(f"/api/admin/users/{self.superuser.id}/suspend/")
        self.assertEqual(protected.status_code, 403)

    def test_no_admin_delete_endpoint(self):
        response = self.client.delete(f"/api/admin/users/{self.target.id}/")
        self.assertEqual(response.status_code, 405)
        self.assertTrue(User.objects.filter(pk=self.target.id).exists())
        self.assertTrue(Listing.objects.filter(user=self.target).exists())


class AdminBusinessMediaTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.staff = User.objects.create_user(
            username="staff7",
            email="staff7@korook.com",
            password="StaffPass!234",
            is_staff=True,
        )
        self.client.post(
            "/api/admin/auth/login/",
            {"username": "staff7", "password": "StaffPass!234"},
            content_type="application/json",
        )
        self.listing = Listing.objects.create(
            user=self.staff,
            title="Media Shop",
            city="LA",
            state="CA",
            contact_info="media@shop.com",
        )

    def _upload(self, name="cover.jpg", content_type="image/jpeg", role="gallery"):
        from django.core.files.uploadedfile import SimpleUploadedFile

        return self.client.post(
            f"/api/admin/businesses/{self.listing.id}/images/",
            {
                "image": SimpleUploadedFile(name, b"fake-image-bytes", content_type=content_type),
                "role": role,
            },
        )

    def test_upload_list_and_validate_image(self):
        invalid = self._upload(name="bad.gif", content_type="image/gif")
        self.assertEqual(invalid.status_code, 400)

        upload = self._upload(role="cover")
        self.assertEqual(upload.status_code, 201)
        self.assertEqual(upload.json()["role"], "cover")
        self.assertIn("filename", upload.json())

        listing = self.client.get(f"/api/admin/businesses/{self.listing.id}/")
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(len(listing.json()["images"]), 1)

        images = self.client.get(f"/api/admin/businesses/{self.listing.id}/images/")
        self.assertEqual(images.status_code, 200)
        self.assertEqual(len(images.json()), 1)

    def test_set_cover_demotes_previous_cover(self):
        first = self._upload(name="cover1.jpg", role="cover")
        second = self._upload(name="cover2.jpg", role="cover")
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)

        first_id = first.json()["id"]
        second_id = second.json()["id"]
        first_image = ListingImage.objects.get(pk=first_id)
        second_image = ListingImage.objects.get(pk=second_id)
        self.assertEqual(first_image.role, ListingImage.Role.GALLERY)
        self.assertEqual(second_image.role, ListingImage.Role.COVER)

    def test_set_logo_action(self):
        gallery = self._upload(name="logo-candidate.jpg", role="gallery")
        image_id = gallery.json()["id"]
        response = self.client.post(
            f"/api/admin/businesses/{self.listing.id}/images/{image_id}/set-logo/"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["role"], "logo")

    def test_replace_delete_and_reorder_gallery(self):
        one = self._upload(name="g1.jpg", role="gallery")
        two = self._upload(name="g2.jpg", role="gallery")
        three = self._upload(name="g3.jpg", role="gallery")
        ids = [one.json()["id"], two.json()["id"], three.json()["id"]]

        reorder = self.client.post(
            f"/api/admin/businesses/{self.listing.id}/images/reorder/",
            {"order": [ids[2], ids[0], ids[1]]},
            content_type="application/json",
        )
        self.assertEqual(reorder.status_code, 200)
        self.assertEqual(reorder.json()[0]["id"], ids[2])

        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.test.client import BOUNDARY, encode_multipart

        replace_body = encode_multipart(
            BOUNDARY,
            {
                "image": SimpleUploadedFile(
                    "replacement.jpg", b"new-bytes", content_type="image/jpeg"
                )
            },
        )
        replace = self.client.patch(
            f"/api/admin/businesses/{self.listing.id}/images/{ids[0]}/",
            replace_body,
            content_type=f"multipart/form-data; boundary={BOUNDARY}",
        )
        self.assertEqual(replace.status_code, 200)

        delete = self.client.delete(
            f"/api/admin/businesses/{self.listing.id}/images/{ids[1]}/"
        )
        self.assertEqual(delete.status_code, 204)
        self.assertFalse(ListingImage.objects.filter(pk=ids[1]).exists())


class AdminEventManagementTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.staff = User.objects.create_user(
            username="staff8",
            email="staff8@korook.com",
            password="StaffPass!234",
            is_staff=True,
        )
        self.owner = User.objects.create_user(
            username="event_owner",
            email="owner@korook.com",
            password="OwnerPass!234",
        )
        self.client.post(
            "/api/admin/auth/login/",
            {"username": "staff8", "password": "StaffPass!234"},
            content_type="application/json",
        )
        self.event = Event.objects.create(
            title="Community Night",
            description="A fun evening",
            category="Community",
            starts_at=timezone.now() + timezone.timedelta(days=3),
            city="Los Angeles",
            state="CA",
            owner=self.owner,
            status=Event.Status.DRAFT,
        )

    def test_event_list_search_filters_and_sort(self):
        response = self.client.get("/api/admin/events/?search=Community")
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(response.json()["count"], 1)
        row = response.json()["results"][0]
        self.assertIn("cover_image_url", row)
        self.assertIn("listing_title", row)

        filtered = self.client.get("/api/admin/events/?status=draft&featured=false")
        self.assertEqual(filtered.status_code, 200)

    def test_event_create_update_and_publish(self):
        create = self.client.post(
            "/api/admin/events/",
            {
                "title": "New Admin Event",
                "description": "Created in tests",
                "category": "Music",
                "starts_at": (timezone.now() + timezone.timedelta(days=5)).isoformat(),
                "city": "LA",
                "state": "CA",
                "owner_id": self.owner.id,
                "status": "draft",
                "tags": ["live", "music"],
                "phone": "555-0100",
            },
            content_type="application/json",
        )
        self.assertEqual(create.status_code, 201)
        event_id = create.json()["id"]
        self.assertEqual(create.json()["tags"], ["live", "music"])

        patch = self.client.patch(
            f"/api/admin/events/{event_id}/",
            {"title": "Updated Event Title", "website": "https://korook.com"},
            content_type="application/json",
        )
        self.assertEqual(patch.status_code, 200)
        self.assertEqual(patch.json()["title"], "Updated Event Title")

        publish = self.client.post(f"/api/admin/events/{event_id}/publish/")
        self.assertEqual(publish.status_code, 200)
        self.assertEqual(publish.json()["status"], "published")

    def test_event_feature_hide_duplicate_delete(self):
        feature = self.client.post(f"/api/admin/events/{self.event.id}/feature/")
        self.assertEqual(feature.status_code, 200)
        self.assertTrue(feature.json()["is_featured"])

        hide = self.client.post(f"/api/admin/events/{self.event.id}/hide/")
        self.assertEqual(hide.status_code, 200)
        self.assertEqual(hide.json()["status"], "hidden")

        duplicate = self.client.post(f"/api/admin/events/{self.event.id}/duplicate/")
        self.assertEqual(duplicate.status_code, 201)
        self.assertTrue(duplicate.json()["title"].startswith("Copy of"))

        delete = self.client.delete(f"/api/admin/events/{duplicate.json()['id']}/")
        self.assertEqual(delete.status_code, 204)

    def test_event_media_upload_gallery_and_reorder(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        cover = self.client.post(
            f"/api/admin/events/{self.event.id}/media/",
            {
                "image": SimpleUploadedFile("cover.jpg", b"cover-bytes", content_type="image/jpeg"),
                "role": "cover",
            },
        )
        self.assertEqual(cover.status_code, 201)
        self.assertIsNotNone(cover.json()["cover_image_url"])

        gallery = self.client.post(
            f"/api/admin/events/{self.event.id}/media/",
            {
                "image": SimpleUploadedFile("g1.jpg", b"g1", content_type="image/jpeg"),
                "role": "gallery",
            },
        )
        self.assertEqual(gallery.status_code, 201)
        image_id = gallery.json()["id"]

        reorder = self.client.post(
            f"/api/admin/events/{self.event.id}/media/reorder/",
            {"order": [image_id]},
            content_type="application/json",
        )
        self.assertEqual(reorder.status_code, 200)

        invalid = self.client.post(
            f"/api/admin/events/{self.event.id}/media/",
            {
                "image": SimpleUploadedFile("bad.gif", b"x", content_type="image/gif"),
                "role": "gallery",
            },
        )
        self.assertEqual(invalid.status_code, 400)

        delete = self.client.delete(
            f"/api/admin/events/{self.event.id}/media/{image_id}/"
        )
        self.assertEqual(delete.status_code, 204)
