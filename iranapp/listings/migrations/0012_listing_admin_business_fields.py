# Generated manually for Korook listing business admin fields

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("listings", "0011_alter_listing_user_cascade"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="listing",
            name="about",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="listing",
            name="address",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="listing",
            name="admin_note",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="listing",
            name="business_name",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="listing",
            name="display_priority",
            field=models.PositiveIntegerField(db_index=True, default=0),
        ),
        migrations.AddField(
            model_name="listing",
            name="instagram",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="listing",
            name="is_sponsored",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="listing",
            name="owner",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="owned_listings",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="listing",
            name="phone",
            field=models.CharField(blank=True, default="", max_length=50),
        ),
        migrations.AddField(
            model_name="listing",
            name="premium_end_date",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="listing",
            name="premium_start_date",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="listing",
            name="premium_status",
            field=models.CharField(
                choices=[
                    ("none", "None"),
                    ("trial", "Trial"),
                    ("active", "Active"),
                    ("expired", "Expired"),
                    ("paused", "Paused"),
                ],
                db_index=True,
                default="none",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="listing",
            name="status",
            field=models.CharField(
                choices=[
                    ("draft", "Draft"),
                    ("published", "Published"),
                    ("hidden", "Hidden"),
                ],
                db_index=True,
                default="published",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="listing",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name="listing",
            name="verified_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="listing",
            name="verified_badge",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="listing",
            name="website",
            field=models.URLField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="listingimage",
            name="media_status",
            field=models.CharField(
                choices=[
                    ("active", "Active"),
                    ("hidden", "Hidden"),
                    ("pending_review", "Pending review"),
                    ("rejected", "Rejected"),
                ],
                db_index=True,
                default="active",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="listingimage",
            name="moderation_reason",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="listingimage",
            name="reviewed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="listingimage",
            name="reviewed_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="listing_image_reviews",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="listingimage",
            name="role",
            field=models.CharField(
                choices=[
                    ("logo", "Logo"),
                    ("cover", "Cover"),
                    ("gallery", "Gallery"),
                ],
                db_index=True,
                default="gallery",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="listingimage",
            name="uploaded_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="uploaded_listing_images",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddIndex(
            model_name="listing",
            index=models.Index(fields=["city", "state"], name="listings_li_city_0bb1d0_idx"),
        ),
    ]
