from django.db import migrations, models


def sync_external_cover_image_url_column(apps, schema_editor):
    """Align PostgreSQL staging column (may pre-exist) with blank default."""
    connection = schema_editor.connection
    if connection.vendor != "postgresql":
        return

    Event = apps.get_model("korook_platform", "Event")
    table = Event._meta.db_table

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = CURRENT_SCHEMA()
              AND table_name = %s
              AND column_name = 'external_cover_image_url'
            """,
            [table],
        )
        if not cursor.fetchone():
            return

        cursor.execute(
            f"""
            UPDATE {table}
            SET external_cover_image_url = ''
            WHERE external_cover_image_url IS NULL
            """
        )
        cursor.execute(
            f"""
            ALTER TABLE {table}
            ALTER COLUMN external_cover_image_url SET DEFAULT ''
            """
        )


def add_external_cover_image_url_column(apps, schema_editor):
    Event = apps.get_model("korook_platform", "Event")
    field = models.URLField(blank=True, default="", max_length=200)
    field.set_attributes_from_name("external_cover_image_url")

    connection = schema_editor.connection
    if connection.vendor == "postgresql":
        table = Event._meta.db_table
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = CURRENT_SCHEMA()
                  AND table_name = %s
                  AND column_name = 'external_cover_image_url'
                """,
                [table],
            )
            if cursor.fetchone():
                return

    schema_editor.add_field(Event, field)


class Migration(migrations.Migration):

    dependencies = [
        ("korook_platform", "0003_businessclaim_submission_fields"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name="event",
                    name="external_cover_image_url",
                    field=models.URLField(blank=True, default="", max_length=200),
                ),
            ],
            database_operations=[
                migrations.RunPython(
                    sync_external_cover_image_url_column,
                    migrations.RunPython.noop,
                ),
                migrations.RunPython(
                    add_external_cover_image_url_column,
                    migrations.RunPython.noop,
                ),
            ],
        ),
    ]
