# Generated manually for Korook mobile verification codes

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="useremailprofile",
            name="verification_code_expires_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="useremailprofile",
            name="verification_code_hash",
            field=models.CharField(blank=True, max_length=128, null=True),
        ),
        migrations.AddField(
            model_name="useremailprofile",
            name="verification_last_sent_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="useremailprofile",
            name="verification_sends_in_window",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="useremailprofile",
            name="verification_window_started_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
