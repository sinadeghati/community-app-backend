# Additive avatar field. Existing rows keep NULL; no data is rewritten.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_external_identity"),
    ]

    operations = [
        migrations.AddField(
            model_name="useremailprofile",
            name="avatar",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to="profiles/avatars/",
            ),
        ),
    ]
