import tempfile

from django.contrib.auth.models import User
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from .models import UserEmailProfile, get_or_create_email_profile

MINIMAL_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
)
MAX_AVATAR_BYTES = 5 * 1024 * 1024
PROFILE_URL = "/api/accounts/profile/"


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class ProfileAvatarTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="avataruser",
            email="avatar@example.com",
            password="SecurePass123!",
        )
        get_or_create_email_profile(self.user).mark_verified()
        self.client.force_authenticate(user=self.user)

    def _png(self, name="avatar.png"):
        return SimpleUploadedFile(name, MINIMAL_PNG, content_type="image/png")

    def test_authenticated_avatar_upload(self):
        response = self.client.patch(
            PROFILE_URL,
            {"avatar": self._png()},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        profile = UserEmailProfile.objects.get(user=self.user)
        self.assertTrue(profile.avatar.name.startswith("profiles/avatars/"))
        self.assertTrue(default_storage.exists(profile.avatar.name))

    def test_absolute_avatar_url_returned(self):
        before = self.client.get(PROFILE_URL)
        self.assertEqual(before.status_code, status.HTTP_200_OK)
        self.assertIsNone(before.data["avatar_url"])

        response = self.client.patch(
            PROFILE_URL,
            {"avatar": self._png()},
            format="multipart",
        )

        avatar_url = response.data["avatar_url"]
        self.assertIsNotNone(avatar_url)
        self.assertTrue(avatar_url.startswith("https://"))
        self.assertIn("/media/profiles/avatars/", avatar_url)
        self.assertNotIn("MEDIA_ROOT", avatar_url)

    def test_avatar_persists_on_later_get(self):
        uploaded = self.client.patch(
            PROFILE_URL,
            {"avatar": self._png()},
            format="multipart",
        )
        self.assertEqual(uploaded.status_code, status.HTTP_200_OK)

        later = self.client.get(PROFILE_URL)

        self.assertEqual(later.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(uploaded.data["avatar_url"])
        self.assertEqual(later.data["avatar_url"], uploaded.data["avatar_url"])
        self.assertEqual(later.data["id"], self.user.id)
        self.assertEqual(later.data["username"], self.user.username)
        self.assertEqual(later.data["email"], self.user.email)
        self.assertTrue(later.data["email_verified"])
        profile = UserEmailProfile.objects.get(user=self.user)
        self.assertTrue(default_storage.exists(profile.avatar.name))

    def test_invalid_file_type_rejected(self):
        response = self.client.patch(
            PROFILE_URL,
            {
                "avatar": SimpleUploadedFile(
                    "notes.txt",
                    b"this is not an image",
                    content_type="text/plain",
                )
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("avatar", response.data)
        profile = UserEmailProfile.objects.get(user=self.user)
        self.assertFalse(profile.avatar)

    def test_oversized_file_rejected(self):
        response = self.client.patch(
            PROFILE_URL,
            {
                "avatar": SimpleUploadedFile(
                    "big.png",
                    b"\x00" * (MAX_AVATAR_BYTES + 1),
                    content_type="image/png",
                )
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("avatar", response.data)
        self.assertIn("5 MB", str(response.data["avatar"]))
        profile = UserEmailProfile.objects.get(user=self.user)
        self.assertFalse(profile.avatar)

    def test_unauthenticated_upload_rejected(self):
        client = APIClient()
        response = client.patch(
            PROFILE_URL,
            {"avatar": self._png()},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        profile = UserEmailProfile.objects.get(user=self.user)
        self.assertFalse(profile.avatar)

    def test_json_patch_preserves_existing_profile_fields(self):
        response = self.client.patch(
            PROFILE_URL,
            {"username": "changed"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "avataruser")
        self.assertIsNone(response.data["avatar_url"])
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "avataruser")
