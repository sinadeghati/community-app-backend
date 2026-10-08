from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import get_or_create_email_profile

from .models import Event


class UserEventApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.password = "SecurePass123!"
        self.owner = User.objects.create_user(
            username="ani",
            email="simon.aab.plumbing@gmail.com",
            password=self.password,
        )
        self.other = User.objects.create_user(
            username="other_user",
            email="other@example.com",
            password=self.password,
        )
        self.staff = User.objects.create_user(
            username="staff",
            email="staff@example.com",
            password=self.password,
            is_staff=True,
        )
        for user in (self.owner, self.other, self.staff):
            get_or_create_email_profile(user).mark_verified()
        self.starts = timezone.now() + timezone.timedelta(days=7)

    def _login(self, username):
        login = self.client.post(
            "/api/accounts/login/",
            {"username": username, "password": self.password},
            format="json",
        )
        self.assertEqual(login.status_code, status.HTTP_200_OK)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    def test_create_assigns_authenticated_owner_ignores_client_owner_id(self):
        self._login("ani")
        response = self.client.post(
            "/api/events/",
            {
                "title": "Staging QA Event",
                "description": "Test",
                "category": "Community Gathering",
                "starts_at": self.starts.isoformat(),
                "city": "San Diego",
                "state": "CA",
                "location": "San Diego, CA",
                "owner_id": self.other.id,
                "is_public": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        event = Event.objects.get(pk=response.data["id"])
        self.assertEqual(event.owner_id, self.owner.id)
        self.assertEqual(event.status, Event.Status.PUBLISHED)

    def test_public_list_published_only(self):
        Event.objects.create(
            owner=self.owner,
            title="Published",
            starts_at=self.starts,
            status=Event.Status.PUBLISHED,
            city="San Diego",
            state="CA",
        )
        Event.objects.create(
            owner=self.owner,
            title="Draft",
            starts_at=self.starts,
            status=Event.Status.DRAFT,
            city="San Diego",
            state="CA",
        )
        response = self.client.get("/api/events/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = [row["title"] for row in response.data]
        self.assertEqual(titles, ["Published"])

    def test_mine_lists_only_authenticated_owner_events(self):
        Event.objects.create(
            owner=self.owner,
            title="Mine",
            starts_at=self.starts,
            status=Event.Status.PUBLISHED,
        )
        Event.objects.create(
            owner=self.other,
            title="Not mine",
            starts_at=self.starts,
            status=Event.Status.PUBLISHED,
        )
        self._login("ani")
        response = self.client.get("/api/events/mine/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "Mine")

    def test_other_user_cannot_patch_or_delete(self):
        event = Event.objects.create(
            owner=self.owner,
            title="Protected",
            starts_at=self.starts,
            status=Event.Status.PUBLISHED,
        )
        self._login("other_user")
        patch = self.client.patch(
            f"/api/events/{event.id}/",
            {"title": "Hacked"},
            format="json",
        )
        self.assertEqual(patch.status_code, status.HTTP_403_FORBIDDEN)
        delete = self.client.delete(f"/api/events/{event.id}/")
        self.assertEqual(delete.status_code, status.HTTP_403_FORBIDDEN)
        event.refresh_from_db()
        self.assertEqual(event.title, "Protected")

    def test_owner_can_update_and_delete(self):
        self._login("ani")
        create = self.client.post(
            "/api/events/",
            {
                "title": "Editable",
                "starts_at": self.starts.isoformat(),
                "city": "Irvine",
                "state": "CA",
            },
            format="json",
        )
        event_id = create.data["id"]
        patch = self.client.patch(
            f"/api/events/{event_id}/",
            {"title": "Updated title"},
            format="json",
        )
        self.assertEqual(patch.status_code, status.HTTP_200_OK)
        self.assertEqual(patch.data["title"], "Updated title")
        delete = self.client.delete(f"/api/events/{event_id}/")
        self.assertEqual(delete.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Event.objects.filter(pk=event_id).exists())

    def test_staff_can_delete_any_event(self):
        event = Event.objects.create(
            owner=self.owner,
            title="Staff delete",
            starts_at=self.starts,
            status=Event.Status.PUBLISHED,
        )
        self._login("staff")
        response = self.client.delete(f"/api/events/{event.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_unauthenticated_create_rejected(self):
        response = self.client.post(
            "/api/events/",
            {"title": "Nope", "starts_at": self.starts.isoformat()},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
