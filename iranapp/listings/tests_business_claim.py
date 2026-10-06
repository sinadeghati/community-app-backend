from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import get_or_create_email_profile
from korook_platform.models import BusinessClaim
from listings.models import Listing
from listings.unclaimed import get_unclaimed_listing_user


class BusinessClaimSubmissionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.password = "SecurePass123!"
        self.claimant = User.objects.create_user(
            username="claimant1",
            email="claimant1@example.com",
            password=self.password,
        )
        get_or_create_email_profile(self.claimant).mark_verified()
        self.other = User.objects.create_user(
            username="other1",
            email="other1@example.com",
            password=self.password,
        )
        get_or_create_email_profile(self.other).mark_verified()
        self.staff = User.objects.create_user(
            username="staff_claim",
            email="staff_claim@korook.com",
            password="StaffPass!234",
            is_staff=True,
        )
        placeholder = get_unclaimed_listing_user()
        self.unclaimed = Listing.objects.create(
            user=placeholder,
            owner=None,
            title="Fair Auto Repair",
            business_name="Fair Auto Repair",
            city="San Diego",
            state="CA",
            contact_info="",
            address="1 Main St",
            category="Automotive",
            status=Listing.Status.PUBLISHED,
        )
        self.claimed = Listing.objects.create(
            user=self.other,
            owner=self.other,
            title="Owned Shop",
            city="LA",
            state="CA",
            contact_info="owned@example.com",
            status=Listing.Status.PUBLISHED,
        )
        self.claim_url = f"/api/listings/{self.unclaimed.id}/claim/"
        self.payload = {
            "claimant_name": "Jane Owner",
            "relationship_role": "Owner",
            "contact_email": "jane@fairauto.com",
            "contact_phone": "555-0100",
            "verification_message": "I am the registered owner of this shop.",
        }

    def _login(self, username):
        response = self.client.post(
            "/api/accounts/login/",
            {"username": username, "password": self.password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def test_claim_submission_requires_authentication(self):
        response = self.client.post(self.claim_url, self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_successful_claim_submission(self):
        self._login("claimant1")
        response = self.client.post(self.claim_url, self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        claim = BusinessClaim.objects.get(listing=self.unclaimed, requester=self.claimant)
        self.assertEqual(claim.status, BusinessClaim.Status.PENDING)
        self.assertEqual(claim.claimant_name, "Jane Owner")
        self.assertEqual(claim.contact_email, "jane@fairauto.com")

    def test_duplicate_pending_claim_rejected(self):
        self._login("claimant1")
        first = self.client.post(self.claim_url, self.payload, format="json")
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        second = self.client.post(self.claim_url, self.payload, format="json")
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)

    def test_already_claimed_business_rejected(self):
        self._login("claimant1")
        url = f"/api/listings/{self.claimed.id}/claim/"
        response = self.client.post(url, self.payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_non_admin_cannot_approve_claim(self):
        claim = BusinessClaim.objects.create(
            listing=self.unclaimed,
            requester=self.claimant,
            status=BusinessClaim.Status.PENDING,
            **{k: v for k, v in self.payload.items() if k != "verification_message"},
            verification_message=self.payload["verification_message"],
        )
        self._login("claimant1")
        response = self.client.post(f"/api/admin/claims/{claim.id}/approve/")
        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_admin_approval_links_existing_user(self):
        claim = BusinessClaim.objects.create(
            listing=self.unclaimed,
            requester=self.claimant,
            status=BusinessClaim.Status.PENDING,
            claimant_name="Jane Owner",
            relationship_role="Owner",
            contact_email="jane@fairauto.com",
            contact_phone="555-0100",
            verification_message="Proof on file.",
        )
        admin = APIClient(enforce_csrf_checks=False)
        admin.post(
            "/api/admin/auth/login/",
            {"username": "staff_claim", "password": "StaffPass!234"},
            content_type="application/json",
        )
        response = admin.post(f"/api/admin/claims/{claim.id}/approve/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.unclaimed.refresh_from_db()
        self.assertEqual(self.unclaimed.owner_id, self.claimant.id)
        self.assertEqual(self.unclaimed.user_id, self.claimant.id)
        claim.refresh_from_db()
        self.assertEqual(claim.status, BusinessClaim.Status.APPROVED)

    def test_admin_rejection_leaves_ownership_unchanged(self):
        claim = BusinessClaim.objects.create(
            listing=self.unclaimed,
            requester=self.claimant,
            status=BusinessClaim.Status.PENDING,
        )
        admin = APIClient(enforce_csrf_checks=False)
        admin.post(
            "/api/admin/auth/login/",
            {"username": "staff_claim", "password": "StaffPass!234"},
            content_type="application/json",
        )
        response = admin.post(
            f"/api/admin/claims/{claim.id}/reject/",
            {"admin_note": "Insufficient proof"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.unclaimed.refresh_from_db()
        self.assertIsNone(self.unclaimed.owner_id)

    def test_approve_fails_when_business_already_claimed(self):
        claim = BusinessClaim.objects.create(
            listing=self.unclaimed,
            requester=self.claimant,
            status=BusinessClaim.Status.PENDING,
        )
        self.unclaimed.owner = self.other
        self.unclaimed.user = self.other
        self.unclaimed.save(update_fields=["owner", "user", "updated_at"])
        admin = APIClient(enforce_csrf_checks=False)
        admin.post(
            "/api/admin/auth/login/",
            {"username": "staff_claim", "password": "StaffPass!234"},
            content_type="application/json",
        )
        response = admin.post(f"/api/admin/claims/{claim.id}/approve/")
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.unclaimed.refresh_from_db()
        self.assertEqual(self.unclaimed.owner_id, self.other.id)

    def test_get_claim_status_for_authenticated_user(self):
        BusinessClaim.objects.create(
            listing=self.unclaimed,
            requester=self.claimant,
            status=BusinessClaim.Status.PENDING,
        )
        self._login("claimant1")
        response = self.client.get(self.claim_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["is_unclaimed"])
        self.assertEqual(response.data["user_claim_status"], "pending")
