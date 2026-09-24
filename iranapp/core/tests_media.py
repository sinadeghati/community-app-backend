from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from listings.models import Listing, ListingImage
from listings.serializers import ListingSerializer


MINIMAL_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
)


@override_settings(SERVE_MEDIA=True)
class MediaUrlAndServingTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.user = User.objects.create_user(username="mediauser", password="pass12345!")
        self.listing = Listing.objects.create(
            user=self.user,
            title="Serve Test",
            city="LA",
            state="CA",
            contact_info="",
            category="Food",
            address="1 Test St",
            status=Listing.Status.PUBLISHED,
        )

    def test_uploaded_file_exists_and_url_is_public(self):
        staff = User.objects.create_user(
            username="staffmedia",
            password="StaffPass!234",
            is_staff=True,
        )
        self.client.post(
            "/api/admin/auth/login/",
            {"username": "staffmedia", "password": "StaffPass!234"},
            content_type="application/json",
        )
        upload = self.client.post(
            f"/api/admin/businesses/{self.listing.id}/images/",
            {
                "image": SimpleUploadedFile("logo.png", MINIMAL_PNG, content_type="image/png"),
                "role": "logo",
            },
        )
        self.assertEqual(upload.status_code, 201)
        body = upload.json()
        self.assertEqual(body["role"], "logo")
        self.assertTrue(body["image"].startswith("listings/"))
        image_url = body["image_url"]
        self.assertIsNotNone(image_url)
        self.assertNotIn("/app/media/", image_url)
        self.assertTrue(image_url.startswith("http"))

        image = ListingImage.objects.get(pk=body["id"])
        self.assertTrue(image.image.storage.exists(image.image.name))

        response = self.client.get(image_url.replace("http://testserver", ""))
        self.assertEqual(response.status_code, 200)
        self.assertIn(response["Content-Type"], ("image/png", "application/octet-stream"))

    def test_public_listing_serializer_returns_mobile_loadable_urls(self):
        image = ListingImage.objects.create(
            listing=self.listing,
            image=SimpleUploadedFile("cover.png", MINIMAL_PNG, content_type="image/png"),
            role=ListingImage.Role.COVER,
        )
        request = self.client.get("/api/listings/").wsgi_request
        data = ListingSerializer(self.listing, context={"request": request}).data
        self.assertIsNotNone(data["cover_image"])
        self.assertNotIn("/app/media/", data["cover_image"])
        self.assertTrue(data["cover_image"].startswith("http"))
        gallery = data["images"][0]
        self.assertEqual(gallery["role"], image.role)
