import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def delete_orphan_listings(apps, schema_editor):
    """Remove listings detached by the previous SET_NULL behavior."""
    Listing = apps.get_model("listings", "Listing")
    Listing.objects.filter(user__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("listings", "0010_listing_latitude_listing_longitude"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(delete_orphan_listings, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="listing",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="listings",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
