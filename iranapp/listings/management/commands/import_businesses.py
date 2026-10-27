import os

from django.core.management.base import BaseCommand, CommandError

from listings.business_import import (
    ImportAbort,
    ImportFileError,
    apply_import_plan,
    build_import_plan,
    format_report,
    parse_business_csv,
)


class Command(BaseCommand):
    help = (
        "Validate a reviewed business CSV. "
        "The default run is a dry-run and writes nothing. "
        "--apply creates draft unclaimed listings only when "
        "RAILWAY_ENVIRONMENT_NAME is Staging."
    )

    def add_arguments(self, parser):
        parser.add_argument("csv_path", help="Path to the reviewed business CSV.")
        parser.add_argument(
            "--apply",
            action="store_true",
            help=(
                "Create draft unclaimed listings. "
                "Refused unless RAILWAY_ENVIRONMENT_NAME is Staging."
            ),
        )

    def handle(self, *args, **options):
        try:
            rows = parse_business_csv(options["csv_path"])
        except ImportFileError as exc:
            raise CommandError(str(exc)) from exc
        if options["apply"] and not _staging_environment():
            raise CommandError(
                "Refusing --apply because RAILWAY_ENVIRONMENT_NAME is not Staging. "
                "No rows were written."
            )
        plan = build_import_plan(rows)
        created = 0
        if options["apply"]:
            try:
                created = apply_import_plan(plan)
            except ImportAbort as exc:
                raise CommandError(str(exc)) from exc
        self.stdout.write(format_report(plan, created=created, applied=options["apply"]))


def _staging_environment() -> bool:
    name = os.environ.get("RAILWAY_ENVIRONMENT_NAME", "")
    return name.strip().casefold() == "staging"
