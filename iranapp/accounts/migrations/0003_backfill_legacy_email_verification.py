"""
One-time release migration: verify existing accounts before the login gate ships.

At production deploy time this marks every user that already exists in the
database as email_verified=True. Users registered after this migration runs
keep the normal default (email_verified=False) and must verify before login.

Rollback: reverse is a no-op. To undo verification for accounts backfilled
here, run a controlled admin/SQL update on production — do not auto-unverify
everyone on migrate backwards.
"""

from django.db import migrations
from django.utils import timezone


def backfill_legacy_verified_users(apps, schema_editor):
    User = apps.get_model("auth", "User")
    Profile = apps.get_model("accounts", "UserEmailProfile")

    verified_at = timezone.now()

    Profile.objects.filter(email_verified=False).update(
        email_verified=True,
        email_verified_at=verified_at,
    )

    users_with_profile = set(
        Profile.objects.values_list("user_id", flat=True)
    )
    legacy_users = User.objects.exclude(pk__in=users_with_profile).iterator()

    profiles_to_create = []
    for user in legacy_users:
        profiles_to_create.append(
            Profile(
                user_id=user.pk,
                email_verified=True,
                email_verified_at=user.date_joined or verified_at,
            )
        )

    if profiles_to_create:
        Profile.objects.bulk_create(profiles_to_create)


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_useremailprofile_verification_codes"),
    ]

    operations = [
        migrations.RunPython(
            backfill_legacy_verified_users,
            migrations.RunPython.noop,
        ),
    ]
