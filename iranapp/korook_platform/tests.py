from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from .models import Event


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
