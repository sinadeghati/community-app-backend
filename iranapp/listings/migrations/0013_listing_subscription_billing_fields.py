"""Align Listing billing/subscription columns with staging schema."""

from django.db import migrations, models


POSTGRES_ENSURE_COLUMNS = """
ALTER TABLE listings_listing
  ADD COLUMN IF NOT EXISTS subscription_status varchar(20) NOT NULL DEFAULT 'none';
ALTER TABLE listings_listing
  ADD COLUMN IF NOT EXISTS plan_name varchar(20) NOT NULL DEFAULT 'free';
ALTER TABLE listings_listing
  ADD COLUMN IF NOT EXISTS billing_cycle varchar(20) NOT NULL DEFAULT '';
ALTER TABLE listings_listing
  ADD COLUMN IF NOT EXISTS subscription_start_date timestamp with time zone NULL;
ALTER TABLE listings_listing
  ADD COLUMN IF NOT EXISTS subscription_end_date timestamp with time zone NULL;
ALTER TABLE listings_listing
  ADD COLUMN IF NOT EXISTS subscription_canceled_at timestamp with time zone NULL;
ALTER TABLE listings_listing
  ADD COLUMN IF NOT EXISTS stripe_customer_id varchar(128) NOT NULL DEFAULT '';
ALTER TABLE listings_listing
  ADD COLUMN IF NOT EXISTS stripe_subscription_id varchar(128) NOT NULL DEFAULT '';
ALTER TABLE listings_listing
  ADD COLUMN IF NOT EXISTS last_payment_status varchar(64) NOT NULL DEFAULT '';
ALTER TABLE listings_listing
  ADD COLUMN IF NOT EXISTS monthly_price_cents integer NULL;
ALTER TABLE listings_listing
  ADD COLUMN IF NOT EXISTS billing_notes text NOT NULL DEFAULT '';
ALTER TABLE listings_listing
  ADD COLUMN IF NOT EXISTS logo_url varchar(200) NOT NULL DEFAULT '';
ALTER TABLE listings_listing
  ADD COLUMN IF NOT EXISTS gallery_urls text NOT NULL DEFAULT '';
ALTER TABLE listings_listing ALTER COLUMN subscription_status SET DEFAULT 'none';
ALTER TABLE listings_listing ALTER COLUMN plan_name SET DEFAULT 'free';
ALTER TABLE listings_listing ALTER COLUMN billing_cycle SET DEFAULT '';
ALTER TABLE listings_listing ALTER COLUMN stripe_customer_id SET DEFAULT '';
ALTER TABLE listings_listing ALTER COLUMN stripe_subscription_id SET DEFAULT '';
ALTER TABLE listings_listing ALTER COLUMN last_payment_status SET DEFAULT '';
ALTER TABLE listings_listing ALTER COLUMN billing_notes SET DEFAULT '';
ALTER TABLE listings_listing ALTER COLUMN logo_url SET DEFAULT '';
ALTER TABLE listings_listing ALTER COLUMN gallery_urls SET DEFAULT '';
"""


def _column_names(schema_editor, table):
    with schema_editor.connection.cursor() as cursor:
        description = schema_editor.connection.introspection.get_table_description(
            cursor, table
        )
    return {column.name for column in description}


def ensure_columns(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(POSTGRES_ENSURE_COLUMNS)
        return

    sqlite_statements = [
        "ALTER TABLE listings_listing ADD COLUMN subscription_status varchar(20) NOT NULL DEFAULT 'none'",
        "ALTER TABLE listings_listing ADD COLUMN plan_name varchar(20) NOT NULL DEFAULT 'free'",
        "ALTER TABLE listings_listing ADD COLUMN billing_cycle varchar(20) NOT NULL DEFAULT ''",
        "ALTER TABLE listings_listing ADD COLUMN subscription_start_date datetime NULL",
        "ALTER TABLE listings_listing ADD COLUMN subscription_end_date datetime NULL",
        "ALTER TABLE listings_listing ADD COLUMN subscription_canceled_at datetime NULL",
        "ALTER TABLE listings_listing ADD COLUMN stripe_customer_id varchar(128) NOT NULL DEFAULT ''",
        "ALTER TABLE listings_listing ADD COLUMN stripe_subscription_id varchar(128) NOT NULL DEFAULT ''",
        "ALTER TABLE listings_listing ADD COLUMN last_payment_status varchar(64) NOT NULL DEFAULT ''",
        "ALTER TABLE listings_listing ADD COLUMN monthly_price_cents integer NULL",
        "ALTER TABLE listings_listing ADD COLUMN billing_notes text NOT NULL DEFAULT ''",
        "ALTER TABLE listings_listing ADD COLUMN logo_url varchar(200) NOT NULL DEFAULT ''",
        "ALTER TABLE listings_listing ADD COLUMN gallery_urls text NOT NULL DEFAULT ''",
    ]
    existing = _column_names(schema_editor, "listings_listing")
    for statement in sqlite_statements:
        column_name = statement.split("ADD COLUMN", 1)[1].strip().split()[0]
        if column_name in existing:
            continue
        schema_editor.execute(statement)


def noop_reverse(apps, schema_editor):
    return


STATE_OPERATIONS = [
    migrations.AddField(
        model_name="listing",
        name="subscription_status",
        field=models.CharField(
            choices=[
                ("none", "None"),
                ("trial", "Trial"),
                ("active", "Active"),
                ("past_due", "Past due"),
                ("canceled", "Canceled"),
                ("expired", "Expired"),
            ],
            db_index=True,
            default="none",
            max_length=20,
        ),
    ),
    migrations.AddField(
        model_name="listing",
        name="plan_name",
        field=models.CharField(
            choices=[
                ("free", "Free"),
                ("premium", "Premium"),
                ("sponsored", "Sponsored"),
            ],
            db_index=True,
            default="free",
            max_length=20,
        ),
    ),
    migrations.AddField(
        model_name="listing",
        name="billing_cycle",
        field=models.CharField(
            blank=True,
            choices=[("monthly", "Monthly"), ("yearly", "Yearly")],
            default="",
            max_length=20,
        ),
    ),
    migrations.AddField(
        model_name="listing",
        name="subscription_start_date",
        field=models.DateTimeField(blank=True, null=True),
    ),
    migrations.AddField(
        model_name="listing",
        name="subscription_end_date",
        field=models.DateTimeField(blank=True, null=True),
    ),
    migrations.AddField(
        model_name="listing",
        name="subscription_canceled_at",
        field=models.DateTimeField(blank=True, null=True),
    ),
    migrations.AddField(
        model_name="listing",
        name="stripe_customer_id",
        field=models.CharField(blank=True, default="", max_length=128),
    ),
    migrations.AddField(
        model_name="listing",
        name="stripe_subscription_id",
        field=models.CharField(blank=True, default="", max_length=128),
    ),
    migrations.AddField(
        model_name="listing",
        name="last_payment_status",
        field=models.CharField(blank=True, default="", max_length=64),
    ),
    migrations.AddField(
        model_name="listing",
        name="monthly_price_cents",
        field=models.PositiveIntegerField(blank=True, null=True),
    ),
    migrations.AddField(
        model_name="listing",
        name="billing_notes",
        field=models.TextField(blank=True, default=""),
    ),
    migrations.AddField(
        model_name="listing",
        name="logo_url",
        field=models.URLField(blank=True, default=""),
    ),
    migrations.AddField(
        model_name="listing",
        name="gallery_urls",
        field=models.TextField(blank=True, default=""),
    ),
]


class Migration(migrations.Migration):

    dependencies = [
        ("listings", "0012_listing_admin_business_fields"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(ensure_columns, noop_reverse),
            ],
            state_operations=STATE_OPERATIONS,
        ),
    ]
