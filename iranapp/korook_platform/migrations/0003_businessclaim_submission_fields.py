from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("korook_platform", "0002_backfill_user_platform_profiles"),
    ]

    operations = [
        migrations.AddField(
            model_name="businessclaim",
            name="claimant_name",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="businessclaim",
            name="relationship_role",
            field=models.CharField(blank=True, default="", max_length=128),
        ),
        migrations.AddField(
            model_name="businessclaim",
            name="contact_email",
            field=models.EmailField(blank=True, default="", max_length=254),
        ),
        migrations.AddField(
            model_name="businessclaim",
            name="contact_phone",
            field=models.CharField(blank=True, default="", max_length=50),
        ),
        migrations.AddField(
            model_name="businessclaim",
            name="verification_message",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddConstraint(
            model_name="businessclaim",
            constraint=models.UniqueConstraint(
                condition=models.Q(status="pending"),
                fields=("listing", "requester"),
                name="unique_pending_business_claim_per_user_listing",
            ),
        ),
    ]
