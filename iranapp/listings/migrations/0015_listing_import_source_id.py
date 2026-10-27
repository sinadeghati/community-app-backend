from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("listings", "0014_listing_index_and_featured_index"),
    ]

    operations = [
        migrations.AddField(
            model_name="listing",
            name="import_source_id",
            field=models.CharField(blank=True, max_length=255, null=True, unique=True),
        ),
    ]
