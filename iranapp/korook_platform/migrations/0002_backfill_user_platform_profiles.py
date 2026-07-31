from django.db import migrations


def backfill_platform_profiles(apps, schema_editor):
    User = apps.get_model("auth", "User")
    Profile = apps.get_model("korook_platform", "UserPlatformProfile")
    for user in User.objects.all().iterator():
        Profile.objects.get_or_create(
            user_id=user.id,
            defaults={
                "role": "admin" if user.is_staff else "user",
                "account_status": "active",
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ("korook_platform", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(backfill_platform_profiles, migrations.RunPython.noop),
    ]
