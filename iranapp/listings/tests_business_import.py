import csv
import os
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError
from django.test import TestCase

from listings.business_import import PLACEHOLDER_EMAIL
from listings.models import Listing
from listings.unclaimed import UNCLAIMED_LISTING_USERNAME

DEFAULT_FIELDS = [
    "business_name",
    "category",
    "address",
    "city",
    "state",
    "source_id",
    "phone",
    "website",
    "email",
    "instagram",
    "description",
    "latitude",
    "longitude",
]


class BusinessImportTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="listing_owner",
            email="listing-owner@example.com",
            password="SecurePass123!",
        )

    def write_csv(self, rows, fieldnames=None):
        columns = list(fieldnames or DEFAULT_FIELDS)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "businesses.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            for row in rows:
                writer.writerow({column: row.get(column, "") for column in columns})
        return str(path)

    def row(self, **overrides):
        data = {
            "business_name": "Negin Kitchen",
            "category": "Food",
            "address": "500 Westwood Blvd",
            "city": "Los Angeles",
            "state": "CA",
            "source_id": "",
            "phone": "",
            "website": "",
            "email": "",
            "instagram": "",
            "description": "",
            "latitude": "",
            "longitude": "",
        }
        data.update(overrides)
        return data

    def run_import(self, path, *, apply=False, environment="Staging"):
        output = StringIO()
        with patch.dict(os.environ, {"RAILWAY_ENVIRONMENT_NAME": environment}):
            args = [path, "--apply"] if apply else [path]
            call_command("import_businesses", *args, stdout=output)
        return output.getvalue()

    def placeholder_count(self):
        return User.objects.filter(username=UNCLAIMED_LISTING_USERNAME).count()

    def existing(self, **overrides):
        data = {
            "user": self.owner,
            "title": "Existing Business",
            "business_name": "Existing Business",
            "city": "San Diego",
            "state": "CA",
            "address": "9 Harbor Dr",
            "contact_info": "existing@example.com",
            "status": Listing.Status.PUBLISHED,
        }
        data.update(overrides)
        return Listing.objects.create(**data)

    def test_dry_run_performs_zero_writes(self):
        path = self.write_csv(
            [self.row(source_id="src-dry", email="dry@example.com")]
        )
        before_users = User.objects.count()
        before_listings = Listing.objects.count()
        with patch("listings.business_import.get_unclaimed_listing_user") as helper:
            output = self.run_import(path, apply=False, environment="Staging")
        helper.assert_not_called()
        self.assertIn("mode: dry-run", output)
        self.assertIn("read: 1", output)
        self.assertIn("valid: 1", output)
        self.assertIn("would_create: 1", output)
        self.assertIn("created: 0", output)
        self.assertEqual(User.objects.count(), before_users)
        self.assertEqual(Listing.objects.count(), before_listings)
        self.assertEqual(self.placeholder_count(), 0)
        self.assertNotIn("dry@example.com", output)

    def test_apply_creates_only_draft_unclaimed_rows(self):
        path = self.write_csv(
            [
                self.row(
                    business_name="Negin Kitchen",
                    source_id="src-negin",
                    phone="(310) 555-0148",
                    website="https://neginkitchen.example",
                    email="hello@neginkitchen.example",
                    instagram="neginkitchen",
                    description="Family kitchen",
                    latitude="34.0635",
                    longitude="-118.4455",
                )
            ]
        )
        output = self.run_import(path, apply=True)
        self.assertIn("mode: apply", output)
        self.assertIn("created: 1", output)
        self.assertIn("not_map_ready: 0", output)
        self.assertNotIn("hello@neginkitchen.example", output)
        self.assertEqual(Listing.objects.count(), 1)
        listing = Listing.objects.get()
        self.assertEqual(listing.status, Listing.Status.DRAFT)
        self.assertIsNone(listing.owner_id)
        self.assertEqual(listing.user.username, UNCLAIMED_LISTING_USERNAME)
        self.assertFalse(listing.user.is_active)
        self.assertFalse(listing.user.has_usable_password())
        self.assertEqual(listing.title, "Negin Kitchen")
        self.assertEqual(listing.business_name, "Negin Kitchen")
        self.assertEqual(listing.category, "Food")
        self.assertEqual(listing.contact_info, "hello@neginkitchen.example")
        self.assertEqual(listing.phone, "(310) 555-0148")
        self.assertEqual(listing.website, "https://neginkitchen.example")
        self.assertEqual(listing.instagram, "neginkitchen")
        self.assertEqual(listing.description, "Family kitchen")
        self.assertFalse(listing.about)
        self.assertEqual(listing.import_source_id, "src-negin")
        self.assertFalse(listing.is_featured)
        self.assertFalse(listing.is_sponsored)
        self.assertEqual(listing.premium_status, Listing.PremiumStatus.NONE)
        self.assertFalse(listing.verified_badge)
        self.assertEqual(listing.logo_url, "")
        self.assertEqual(listing.gallery_urls, "")
        self.assertEqual(listing.images.count(), 0)
        self.assertAlmostEqual(listing.latitude, 34.0635)
        self.assertAlmostEqual(listing.longitude, -118.4455)

    def test_valid_placeholder_is_reused_without_account_changes(self):
        placeholder = User.objects.create_user(
            username=UNCLAIMED_LISTING_USERNAME,
            email=PLACEHOLDER_EMAIL,
            password="PlaceholderPassword123!",
            first_name="Reserved",
            last_name="Placeholder",
        )
        placeholder.is_active = False
        placeholder.save(update_fields=["is_active"])
        before = self.account_snapshot(placeholder)
        path = self.write_csv(
            [
                self.row(
                    business_name="Reused Placeholder Cafe",
                    address="10 Reserved St",
                    source_id="src-reused-placeholder",
                )
            ]
        )
        with patch(
            "listings.business_import.get_unclaimed_listing_user",
            side_effect=AssertionError("placeholder write"),
        ):
            output = self.run_import(path, apply=True)
        self.assertIn("created: 1", output)
        listing = Listing.objects.get()
        self.assertEqual(listing.user_id, placeholder.id)
        self.assertEqual(listing.status, Listing.Status.DRAFT)
        self.assertIsNone(listing.owner_id)
        self.assertEqual(User.objects.filter(username=UNCLAIMED_LISTING_USERNAME).count(), 1)
        placeholder.refresh_from_db()
        self.assertEqual(self.account_snapshot(placeholder), before)
        self.assertTrue(placeholder.check_password("PlaceholderPassword123!"))

    def test_username_collision_aborts_before_any_write(self):
        real = User.objects.create_user(
            username=UNCLAIMED_LISTING_USERNAME,
            email="real-person@example.com",
            password="RealPassword123!",
            first_name="Real",
            last_name="Owner",
        )
        path = self.write_csv(
            [
                self.row(
                    business_name="Should Not Create",
                    address="1 Collision St",
                    source_id="src-username-collision",
                )
            ]
        )
        self.assert_apply_aborts_without_writes(path, real)

    def test_email_collision_aborts_before_any_write(self):
        real = User.objects.create_user(
            username="real_email_owner",
            email=PLACEHOLDER_EMAIL,
            password="RealPassword123!",
            first_name="Real",
            last_name="Email",
        )
        path = self.write_csv(
            [
                self.row(
                    business_name="Should Not Create Email",
                    address="2 Collision St",
                    source_id="src-email-collision",
                )
            ]
        )
        self.assert_apply_aborts_without_writes(path, real)
        self.assertEqual(self.placeholder_count(), 0)

    def account_snapshot(self, user):
        user.refresh_from_db()
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "password": user.password,
            "is_active": user.is_active,
            "is_staff": user.is_staff,
            "is_superuser": user.is_superuser,
            "first_name": user.first_name,
            "last_name": user.last_name,
        }

    def assert_apply_aborts_without_writes(self, path, account):
        before_users = User.objects.count()
        before_account = self.account_snapshot(account)
        with patch.object(
            Listing.objects,
            "create",
            side_effect=AssertionError("listing write"),
        ):
            with patch(
                "listings.business_import.get_unclaimed_listing_user",
                side_effect=AssertionError("placeholder write"),
            ):
                with self.assertRaises(CommandError) as caught:
                    self.run_import(path, apply=True)
        message = str(caught.exception)
        self.assertIn("no changes", message)
        self.assertNotIn(account.email, message)
        self.assertNotIn("RealPassword123!", message)
        account.refresh_from_db()
        self.assertEqual(self.account_snapshot(account), before_account)
        self.assertTrue(account.check_password("RealPassword123!"))
        self.assertEqual(User.objects.count(), before_users)
        self.assertEqual(Listing.objects.count(), 0)

    def test_duplicate_import_source_id(self):
        existing = self.existing(
            import_source_id="src-kept",
            is_featured=True,
            title="Kept Name",
            business_name="Kept Name",
        )
        path = self.write_csv(
            [
                self.row(
                    business_name="Different Name",
                    address="100 Other St",
                    city="Irvine",
                    state="CA",
                    source_id="src-kept",
                    phone="(949) 555-0101",
                    website="https://different.example",
                )
            ]
        )
        output = self.run_import(path, apply=True)
        self.assertIn("duplicate: 1", output)
        self.assertIn("row 2: duplicate import_source_id (existing listing", output)
        self.assertIn("created: 0", output)
        existing.refresh_from_db()
        self.assertEqual(existing.title, "Kept Name")
        self.assertTrue(existing.is_featured)
        self.assertEqual(existing.status, Listing.Status.PUBLISHED)
        self.assertEqual(Listing.objects.count(), 1)

    def test_duplicate_phone(self):
        existing = self.existing(phone="(310) 555-0199")
        path = self.write_csv(
            [
                self.row(
                    business_name="Phone Match",
                    address="77 Other Ave",
                    city="Irvine",
                    phone="310.555.0199",
                    source_id="src-phone",
                )
            ]
        )
        output = self.run_import(path, apply=True)
        self.assertIn("row 2: duplicate phone (existing listing", output)
        self.assertNotIn("5550199", output)
        self.assertNotIn("555-0199", output)
        existing.refresh_from_db()
        self.assertEqual(existing.phone, "(310) 555-0199")
        self.assertEqual(existing.business_name, "Existing Business")
        self.assertEqual(Listing.objects.count(), 1)

    def test_duplicate_website_hostname(self):
        existing = self.existing(website="https://www.Example.com/menu?x=1#top")
        path = self.write_csv(
            [
                self.row(
                    business_name="Website Match",
                    address="88 Other Ave",
                    city="Irvine",
                    website="http://example.com/other",
                    source_id="src-web",
                )
            ]
        )
        output = self.run_import(path, apply=True)
        self.assertIn("row 2: duplicate website (existing listing", output)
        self.assertNotIn("example.com", output)
        existing.refresh_from_db()
        self.assertEqual(existing.website, "https://www.Example.com/menu?x=1#top")
        self.assertEqual(Listing.objects.count(), 1)

    def test_duplicate_name_address_city_state(self):
        existing = self.existing(
            title="Joe's Cafe",
            business_name="Joe's Cafe",
            address="123 Main St.",
            city="Los Angeles",
            state="CA",
        )
        path = self.write_csv(
            [
                self.row(
                    business_name="joes cafe",
                    address="123 main st",
                    city="los angeles",
                    state="ca",
                    source_id="src-address",
                )
            ]
        )
        output = self.run_import(path, apply=True)
        self.assertIn(
            "row 2: duplicate name, address, city, and state (existing listing",
            output,
        )
        existing.refresh_from_db()
        self.assertEqual(existing.business_name, "Joe's Cafe")
        self.assertEqual(existing.status, Listing.Status.PUBLISHED)
        self.assertEqual(Listing.objects.count(), 1)

    def test_duplicate_name_city_coordinates(self):
        existing = self.existing(
            title="Atlas Dental",
            business_name="Atlas Dental",
            address="10 Oak Ave",
            city="Irvine",
            state="CA",
            latitude=34.05221,
            longitude=-118.24371,
        )
        path = self.write_csv(
            [
                self.row(
                    business_name="Atlas Dental",
                    address="99 Pine Rd",
                    city="Irvine",
                    state="CA",
                    latitude="34.05224",
                    longitude="-118.24374",
                    source_id="src-coord",
                )
            ]
        )
        output = self.run_import(path, apply=True)
        self.assertIn(
            "row 2: duplicate name, city, and coordinates (existing listing",
            output,
        )
        existing.refresh_from_db()
        self.assertEqual(existing.address, "10 Oak Ave")
        self.assertEqual(Listing.objects.count(), 1)

    def test_duplicate_rows_within_one_csv(self):
        path = self.write_csv(
            [
                self.row(
                    business_name="First Cafe",
                    address="1 First St",
                    source_id="batch-1",
                    phone="(310) 555-0101",
                ),
                self.row(
                    business_name="Second Cafe",
                    address="2 Second St",
                    source_id="batch-1",
                    phone="(310) 555-0102",
                ),
                self.row(
                    business_name="Third Cafe",
                    address="3 Third St",
                    source_id="batch-2",
                    phone="(310) 555-0103",
                ),
            ]
        )
        output = self.run_import(path, apply=True)
        self.assertIn("read: 3", output)
        self.assertIn("valid: 2", output)
        self.assertIn("created: 2", output)
        self.assertIn("duplicate: 1", output)
        self.assertIn("row 3: duplicate import_source_id (earlier row 2)", output)
        names = set(Listing.objects.values_list("business_name", flat=True))
        self.assertEqual(names, {"First Cafe", "Third Cafe"})

    def test_repeated_import_is_idempotent(self):
        path = self.write_csv(
            [self.row(business_name="Once Cafe", source_id="src-once")]
        )
        first = self.run_import(path, apply=True)
        self.assertIn("created: 1", first)
        listing = Listing.objects.get()
        second = self.run_import(path, apply=True)
        self.assertIn("created: 0", second)
        self.assertIn("would_create: 0", second)
        self.assertIn("duplicate: 1", second)
        self.assertIn("row 2: duplicate import_source_id (existing listing", second)
        self.assertEqual(Listing.objects.count(), 1)
        listing.refresh_from_db()
        self.assertEqual(listing.business_name, "Once Cafe")
        self.assertEqual(listing.status, Listing.Status.DRAFT)
        self.assertEqual(listing.import_source_id, "src-once")

    def test_invalid_category_and_missing_required_fields(self):
        path = self.write_csv(
            [
                self.row(
                    business_name="Bad Category Cafe",
                    category="Restaurants",
                    address="1 Bad St",
                    source_id="src-bad-category",
                ),
                self.row(
                    business_name="Missing City Cafe",
                    city="",
                    address="2 Bad St",
                    source_id="src-missing-city",
                ),
                self.row(
                    business_name="Valid Cafe",
                    address="3 Good St",
                    source_id="src-valid",
                ),
            ]
        )
        output = self.run_import(path, apply=True)
        self.assertIn("read: 3", output)
        self.assertIn("valid: 1", output)
        self.assertIn("invalid: 2", output)
        self.assertIn("skipped: 2", output)
        self.assertIn("created: 1", output)
        self.assertIn(
            "row 2: category must exactly match a Korook business category",
            output,
        )
        self.assertIn("row 3: missing required field: city", output)
        self.assertEqual(
            list(Listing.objects.values_list("business_name", flat=True)),
            ["Valid Cafe"],
        )

    def test_one_sided_and_zero_coordinates_are_rejected(self):
        path = self.write_csv(
            [
                self.row(
                    business_name="Latitude Only",
                    address="1 Coord St",
                    latitude="34.05",
                    longitude="",
                    source_id="src-lat",
                ),
                self.row(
                    business_name="Longitude Only",
                    address="2 Coord St",
                    latitude="",
                    longitude="-118.25",
                    source_id="src-lng",
                ),
                self.row(
                    business_name="Null Island",
                    address="3 Coord St",
                    latitude="0.0",
                    longitude="0.0",
                    source_id="src-zero",
                ),
                self.row(
                    business_name="Has Coordinates",
                    address="4 Coord St",
                    latitude="34.0500",
                    longitude="-118.2500",
                    source_id="src-good-coord",
                ),
            ]
        )
        output = self.run_import(path, apply=True)
        self.assertIn("invalid: 3", output)
        self.assertIn("created: 1", output)
        self.assertIn(
            "row 2: latitude and longitude must both be present or both be empty",
            output,
        )
        self.assertIn(
            "row 3: latitude and longitude must both be present or both be empty",
            output,
        )
        self.assertIn("row 4: coordinates 0,0 are invalid", output)
        self.assertEqual(
            list(Listing.objects.values_list("business_name", flat=True)),
            ["Has Coordinates"],
        )

    def test_missing_coordinates_are_allowed_but_not_map_ready(self):
        path = self.write_csv(
            [self.row(business_name="No Map Cafe", source_id="src-no-map")],
            fieldnames=[
                "business_name",
                "category",
                "address",
                "city",
                "state",
                "source_id",
            ],
        )
        output = self.run_import(path, apply=True)
        self.assertIn("valid: 1", output)
        self.assertIn("created: 1", output)
        self.assertIn("invalid: 0", output)
        self.assertIn("not_map_ready: 1", output)
        self.assertIn("not_map_ready_rows: 2", output)
        listing = Listing.objects.get()
        self.assertIsNone(listing.latitude)
        self.assertIsNone(listing.longitude)
        self.assertEqual(listing.status, Listing.Status.DRAFT)
        self.assertEqual(listing.business_name, "No Map Cafe")

    def test_claimed_and_published_listings_remain_unchanged(self):
        claimed = self.existing(
            user=self.owner,
            owner=self.owner,
            title="Claimed Published",
            business_name="Claimed Published",
            phone="(213) 555-0177",
            status=Listing.Status.PUBLISHED,
            is_featured=True,
            is_sponsored=True,
            premium_status=Listing.PremiumStatus.ACTIVE,
            verified_badge=True,
        )
        published_unclaimed = self.existing(
            user=self.owner,
            owner=None,
            title="Published Unclaimed",
            business_name="Published Unclaimed",
            address="50 Public Ave",
            website="https://www.published.example/path",
            status=Listing.Status.PUBLISHED,
        )
        before = {
            claimed.pk: self.snapshot(claimed),
            published_unclaimed.pk: self.snapshot(published_unclaimed),
        }
        path = self.write_csv(
            [
                self.row(
                    business_name="Should Not Replace Claimed",
                    address="8 New St",
                    city="Fresno",
                    phone="213.555.0177",
                    source_id="src-claimed",
                ),
                self.row(
                    business_name="Should Not Replace Published",
                    address="9 New St",
                    city="Fresno",
                    website="http://published.example/other",
                    source_id="src-published",
                ),
            ]
        )
        output = self.run_import(path, apply=True)
        self.assertIn("created: 0", output)
        self.assertIn("duplicate: 2", output)
        self.assertEqual(Listing.objects.count(), 2)
        claimed.refresh_from_db()
        published_unclaimed.refresh_from_db()
        self.assertEqual(self.snapshot(claimed), before[claimed.pk])
        self.assertEqual(self.snapshot(published_unclaimed), before[published_unclaimed.pk])
        self.assertEqual(claimed.status, Listing.Status.PUBLISHED)
        self.assertEqual(claimed.owner_id, self.owner.id)
        self.assertTrue(claimed.is_featured)
        self.assertTrue(claimed.is_sponsored)
        self.assertEqual(claimed.premium_status, Listing.PremiumStatus.ACTIVE)
        self.assertEqual(published_unclaimed.status, Listing.Status.PUBLISHED)
        self.assertIsNone(published_unclaimed.owner_id)

    def test_forbidden_columns_reject_the_file(self):
        path = self.write_csv(
            [self.row(business_name="Should Not Import", source_id="src-forbidden")],
            fieldnames=[
                "business_name",
                "category",
                "address",
                "city",
                "state",
                "photo",
                "Reviews",
            ],
        )
        with self.assertRaises(CommandError) as caught:
            self.run_import(path, apply=True, environment="Staging")
        message = str(caught.exception)
        self.assertIn("forbidden", message)
        self.assertIn("photo", message)
        self.assertIn("reviews", message)
        self.assertEqual(Listing.objects.count(), 0)
        self.assertEqual(self.placeholder_count(), 0)

    def test_apply_allows_normalized_staging_environment_name(self):
        for index, name in enumerate(("Staging", "staging", "STAGING"), start=1):
            with self.subTest(environment=name):
                path = self.write_csv(
                    [
                        self.row(
                            business_name=f"Gate Business {index}",
                            address=f"{index}00 Gate Road",
                            source_id=f"src-gate-{index}",
                        )
                    ]
                )
                before = Listing.objects.count()
                output = self.run_import(path, apply=True, environment=name)
                self.assertIn("mode: apply", output)
                self.assertIn("created: 1", output)
                self.assertEqual(Listing.objects.count(), before + 1)
                listing = Listing.objects.get(import_source_id=f"src-gate-{index}")
                self.assertEqual(listing.status, Listing.Status.DRAFT)
                self.assertIsNone(listing.owner_id)
                self.assertEqual(listing.user.username, UNCLAIMED_LISTING_USERNAME)
        self.assertEqual(self.placeholder_count(), 1)

    def test_apply_refused_outside_staging(self):
        path = self.write_csv(
            [self.row(business_name="Not Written", source_id="src-outside")]
        )
        cases = (
            ("production", {"RAILWAY_ENVIRONMENT_NAME": "Production"}, False),
            ("blank", {"RAILWAY_ENVIRONMENT_NAME": ""}, False),
            ("unset", {}, True),
            ("obsolete", {"RAILWAY_ENVIRONMENT": "Staging"}, True),
        )
        for label, environment, clear_name in cases:
            with self.subTest(environment=label):
                with patch(
                    "listings.business_import.get_unclaimed_listing_user"
                ) as helper:
                    with patch.dict(os.environ, environment, clear=False):
                        if clear_name:
                            os.environ.pop("RAILWAY_ENVIRONMENT_NAME", None)
                        with self.assertRaises(CommandError) as caught:
                            call_command("import_businesses", path, "--apply")
                helper.assert_not_called()
                self.assertIn("RAILWAY_ENVIRONMENT_NAME", str(caught.exception))
                self.assertIn("No rows were written", str(caught.exception))
                self.assertEqual(Listing.objects.count(), 0)
                self.assertEqual(self.placeholder_count(), 0)

    def test_database_failure_rolls_back_the_full_transaction(self):
        path = self.write_csv(
            [
                self.row(
                    business_name="First Rollback",
                    address="1 Rollback St",
                    source_id="src-rollback-1",
                ),
                self.row(
                    business_name="Second Rollback",
                    address="2 Rollback St",
                    source_id="src-rollback-2",
                ),
            ]
        )
        real_create = Listing.objects.create
        calls = {"count": 0}

        def fail_on_second_create(**kwargs):
            calls["count"] += 1
            if calls["count"] >= 2:
                raise IntegrityError("forced failure")
            return real_create(**kwargs)

        with patch.dict(os.environ, {"RAILWAY_ENVIRONMENT_NAME": "Staging"}):
            with patch.object(Listing.objects, "create", side_effect=fail_on_second_create):
                with self.assertRaises(CommandError) as caught:
                    call_command("import_businesses", path, "--apply")
        self.assertIn("rolled back", str(caught.exception))
        self.assertEqual(calls["count"], 2)
        self.assertEqual(Listing.objects.count(), 0)
        self.assertEqual(self.placeholder_count(), 0)
        self.assertFalse(
            Listing.objects.filter(business_name="First Rollback").exists()
        )

    def snapshot(self, listing):
        return {
            "title": listing.title,
            "business_name": listing.business_name,
            "status": listing.status,
            "owner_id": listing.owner_id,
            "user_id": listing.user_id,
            "phone": listing.phone,
            "website": listing.website,
            "address": listing.address,
            "city": listing.city,
            "state": listing.state,
            "is_featured": listing.is_featured,
            "is_sponsored": listing.is_sponsored,
            "premium_status": listing.premium_status,
            "verified_badge": listing.verified_badge,
            "import_source_id": listing.import_source_id,
            "updated_at": listing.updated_at,
        }
