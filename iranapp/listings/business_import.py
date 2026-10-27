"""Validate a reviewed business CSV and create draft unclaimed listings."""

from __future__ import annotations

import csv
import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from urllib.parse import urlsplit

from django.contrib.auth.models import User
from django.core.validators import EmailValidator, ValidationError
from django.db import DatabaseError, transaction

from listings.categories import BUSINESS_CATEGORIES
from listings.models import Listing
from listings.unclaimed import UNCLAIMED_LISTING_USERNAME, get_unclaimed_listing_user

REQUIRED_COLUMNS = (
    "business_name",
    "category",
    "address",
    "city",
    "state",
)
OPTIONAL_COLUMNS = (
    "source_id",
    "phone",
    "website",
    "email",
    "instagram",
    "description",
    "latitude",
    "longitude",
)
FORBIDDEN_COLUMNS = frozenset(
    {"photo", "image", "logo", "rating", "review", "reviews"}
)
PLACEHOLDER_EMAIL = "unclaimed-listings@korook.internal"
CATEGORY_VALUES = frozenset(BUSINESS_CATEGORIES)
_EMAIL_VALIDATOR = EmailValidator()
_FOUR_PLACES = Decimal("0.0001")


class ImportFileError(Exception):
    """The CSV cannot be imported as a file."""


class ImportAbort(Exception):
    """Apply stopped before or during writing, with nothing left saved."""


@dataclass(frozen=True)
class RowIssue:
    row_number: int
    reason: str


@dataclass(frozen=True)
class PreparedListing:
    row_number: int
    business_name: str
    category: str
    address: str
    city: str
    state: str
    source_id: str | None
    phone: str
    website: str
    email: str
    instagram: str
    description: str
    latitude: float | None
    longitude: float | None
    map_ready: bool


@dataclass(frozen=True)
class ImportPlan:
    read_count: int
    valid: tuple[PreparedListing, ...]
    invalid_rows: tuple[RowIssue, ...]
    duplicate_rows: tuple[RowIssue, ...]
    not_map_ready_rows: tuple[int, ...]

    @property
    def valid_count(self) -> int:
        return len(self.valid)

    @property
    def duplicate_count(self) -> int:
        return len(self.duplicate_rows)

    @property
    def invalid_count(self) -> int:
        return len(self.invalid_rows)

    @property
    def skipped_count(self) -> int:
        return self.invalid_count + self.duplicate_count

    @property
    def not_map_ready_count(self) -> int:
        return len(self.not_map_ready_rows)


@dataclass(frozen=True)
class _MatchKeys:
    source_id: str | None
    phone: str | None
    website: str | None
    address: str | None
    coordinates: str | None


class _KeyIndex:
    def __init__(self) -> None:
        self.source_ids: dict[str, str] = {}
        self.phones: dict[str, str] = {}
        self.websites: dict[str, str] = {}
        self.addresses: dict[str, str] = {}
        self.coordinates: dict[str, str] = {}

    def match(self, keys: _MatchKeys) -> str | None:
        if keys.source_id and keys.source_id in self.source_ids:
            return f"duplicate import_source_id ({self.source_ids[keys.source_id]})"
        if keys.phone and keys.phone in self.phones:
            return f"duplicate phone ({self.phones[keys.phone]})"
        if keys.website and keys.website in self.websites:
            return f"duplicate website ({self.websites[keys.website]})"
        if keys.address and keys.address in self.addresses:
            return (
                "duplicate name, address, city, and state "
                f"({self.addresses[keys.address]})"
            )
        if keys.coordinates and keys.coordinates in self.coordinates:
            return (
                "duplicate name, city, and coordinates "
                f"({self.coordinates[keys.coordinates]})"
            )
        return None

    def add(self, keys: _MatchKeys, label: str) -> None:
        if keys.source_id and keys.source_id not in self.source_ids:
            self.source_ids[keys.source_id] = label
        if keys.phone and keys.phone not in self.phones:
            self.phones[keys.phone] = label
        if keys.website and keys.website not in self.websites:
            self.websites[keys.website] = label
        if keys.address and keys.address not in self.addresses:
            self.addresses[keys.address] = label
        if keys.coordinates and keys.coordinates not in self.coordinates:
            self.coordinates[keys.coordinates] = label


def parse_business_csv(csv_path: str) -> list[tuple[int, dict[str, str]]]:
    path = Path(csv_path)
    if not path.is_file():
        raise ImportFileError("Input file was not found.")
    try:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            fieldnames = reader.fieldnames
            if not fieldnames:
                raise ImportFileError("Input file has no header row.")
            headers = _normalized_headers(fieldnames)
            _reject_forbidden_headers(headers)
            _reject_missing_headers(headers)
            rows: list[tuple[int, dict[str, str]]] = []
            for row_number, raw in enumerate(reader, start=2):
                rows.append((row_number, _cells(raw)))
            return rows
    except UnicodeDecodeError as exc:
        raise ImportFileError("Input file must be UTF-8.") from exc
    except csv.Error as exc:
        raise ImportFileError("Input file is not a valid CSV.") from exc


def build_import_plan(rows: list[tuple[int, dict[str, str]]]) -> ImportPlan:
    index = _KeyIndex()
    _index_existing_listings(index)
    valid: list[PreparedListing] = []
    invalid_rows: list[RowIssue] = []
    duplicate_rows: list[RowIssue] = []
    for row_number, cells in rows:
        prepared, issues = _prepare_row(row_number, cells)
        if issues or prepared is None:
            invalid_rows.append(
                RowIssue(row_number, "; ".join(issues) or "row is invalid")
            )
            continue
        keys = _keys_for_prepared(prepared)
        duplicate = index.match(keys)
        if duplicate:
            duplicate_rows.append(RowIssue(row_number, duplicate))
            continue
        index.add(keys, f"earlier row {row_number}")
        valid.append(prepared)
    not_map_ready = tuple(
        item.row_number for item in valid if not item.map_ready
    )
    return ImportPlan(
        read_count=len(rows),
        valid=tuple(valid),
        invalid_rows=tuple(invalid_rows),
        duplicate_rows=tuple(duplicate_rows),
        not_map_ready_rows=not_map_ready,
    )


def apply_import_plan(plan: ImportPlan) -> int:
    if not plan.valid:
        return 0
    # Read-only identity check. A mismatch raises before any database write.
    user = resolve_unclaimed_user()
    try:
        with transaction.atomic():
            if user is None:
                user = resolve_unclaimed_user()
            if user is None:
                user = get_unclaimed_listing_user()
            for record in plan.valid:
                Listing.objects.create(
                    user=user,
                    owner=None,
                    title=record.business_name,
                    business_name=record.business_name,
                    category=record.category,
                    address=record.address,
                    city=record.city,
                    state=record.state,
                    contact_info=record.email,
                    phone=record.phone,
                    website=record.website,
                    instagram=record.instagram,
                    description=record.description,
                    latitude=record.latitude,
                    longitude=record.longitude,
                    status=Listing.Status.DRAFT,
                    is_featured=False,
                    is_sponsored=False,
                    premium_status=Listing.PremiumStatus.NONE,
                    verified_badge=False,
                    import_source_id=record.source_id,
                )
            return len(plan.valid)
    except ImportAbort:
        raise
    except DatabaseError as exc:
        raise ImportAbort("Import failed and was rolled back.") from exc


def resolve_unclaimed_user() -> User | None:
    """Return the reserved placeholder, or None when it does not exist yet.

    This function only reads. A username or email collision raises before the
    caller creates a user or a listing.
    """
    username_matches = list(
        User.objects.filter(username=UNCLAIMED_LISTING_USERNAME).order_by("id")[:2]
    )
    if len(username_matches) > 1:
        raise ImportAbort(
            "Unclaimed placeholder identity does not match the reserved account. "
            "Import aborted with no changes."
        )
    email_holders = list(
        User.objects.filter(email=PLACEHOLDER_EMAIL).order_by("id")[:2]
    )
    if any(user.username != UNCLAIMED_LISTING_USERNAME for user in email_holders):
        raise ImportAbort(
            "Unclaimed placeholder identity does not match the reserved account. "
            "Import aborted with no changes."
        )
    if len(email_holders) > 1:
        raise ImportAbort(
            "Unclaimed placeholder identity does not match the reserved account. "
            "Import aborted with no changes."
        )
    placeholder = username_matches[0] if username_matches else None
    if placeholder is None:
        return None
    if placeholder.email != PLACEHOLDER_EMAIL:
        raise ImportAbort(
            "Unclaimed placeholder identity does not match the reserved account. "
            "Import aborted with no changes."
        )
    return placeholder


def format_report(plan: ImportPlan, *, created: int, applied: bool) -> str:
    lines = [
        f"mode: {'apply' if applied else 'dry-run'}",
        f"read: {plan.read_count}",
        f"valid: {plan.valid_count}",
        f"would_create: {plan.valid_count}",
        f"created: {created if applied else 0}",
        f"duplicate: {plan.duplicate_count}",
        f"invalid: {plan.invalid_count}",
        f"skipped: {plan.skipped_count}",
        f"not_map_ready: {plan.not_map_ready_count}",
        "not_map_ready_rows: "
        + (", ".join(str(number) for number in plan.not_map_ready_rows) or "-"),
        "invalid_rows:",
    ]
    if plan.invalid_rows:
        lines.extend(
            f"row {issue.row_number}: {issue.reason}" for issue in plan.invalid_rows
        )
    else:
        lines.append("-")
    lines.append("duplicate_rows:")
    if plan.duplicate_rows:
        lines.extend(
            f"row {issue.row_number}: {issue.reason}" for issue in plan.duplicate_rows
        )
    else:
        lines.append("-")
    return "\n".join(lines)


def _normalized_headers(fieldnames: list[str | None]) -> list[str]:
    headers: list[str] = []
    for name in fieldnames:
        header = (name or "").strip().lower()
        if not header:
            raise ImportFileError("Input file has an empty column name.")
        if header in headers:
            raise ImportFileError(f"Input file has a duplicate column: {header}.")
        headers.append(header)
    return headers


def _reject_forbidden_headers(headers: list[str]) -> None:
    found = sorted(set(headers) & FORBIDDEN_COLUMNS)
    if found:
        raise ImportFileError(
            "Input file rejected because it contains forbidden column(s): "
            + ", ".join(found)
            + "."
        )


def _reject_missing_headers(headers: list[str]) -> None:
    missing = [name for name in REQUIRED_COLUMNS if name not in headers]
    if missing:
        raise ImportFileError(
            "Input file is missing required column(s): " + ", ".join(missing) + "."
        )


def _cells(raw: dict[str | None, str | None]) -> dict[str, str]:
    cells: dict[str, str] = {}
    for key, value in raw.items():
        if key is None:
            continue
        cells[key.strip().lower()] = "" if value is None else value.strip()
    return cells


def _prepare_row(
    row_number: int, cells: dict[str, str]
) -> tuple[PreparedListing | None, list[str]]:
    values = {
        column: cells.get(column, "").strip()
        for column in REQUIRED_COLUMNS + OPTIONAL_COLUMNS
    }
    reasons: list[str] = []
    missing = [name for name in REQUIRED_COLUMNS if not values[name]]
    if missing:
        reasons.append("missing required field: " + ", ".join(missing))
    category = values["category"]
    if category and category not in CATEGORY_VALUES:
        reasons.append("category must exactly match a Korook business category")
    reasons.extend(_length_issues(values))
    email = values["email"]
    if email and not _valid_email(email):
        reasons.append("email is not a valid address")
    website = values["website"]
    if website and not website_hostname(website):
        reasons.append("website has no hostname")
    latitude, longitude, coordinate_issue = _parse_coordinates(
        values["latitude"], values["longitude"]
    )
    if coordinate_issue:
        reasons.append(coordinate_issue)
    if reasons:
        return None, reasons
    source_id = values["source_id"] or None
    return (
        PreparedListing(
            row_number=row_number,
            business_name=values["business_name"],
            category=category,
            address=values["address"],
            city=values["city"],
            state=values["state"],
            source_id=source_id,
            phone=values["phone"],
            website=website,
            email=email,
            instagram=values["instagram"],
            description=values["description"],
            latitude=None if latitude is None else float(latitude),
            longitude=None if longitude is None else float(longitude),
            map_ready=latitude is not None and longitude is not None,
        ),
        [],
    )


def _length_issues(values: dict[str, str]) -> list[str]:
    limits = {
        "business_name": Listing._meta.get_field("title").max_length,
        "category": Listing._meta.get_field("category").max_length,
        "address": Listing._meta.get_field("address").max_length,
        "city": Listing._meta.get_field("city").max_length,
        "state": Listing._meta.get_field("state").max_length,
        "source_id": Listing._meta.get_field("import_source_id").max_length,
        "phone": Listing._meta.get_field("phone").max_length,
        "website": Listing._meta.get_field("website").max_length,
        "email": Listing._meta.get_field("contact_info").max_length,
        "instagram": Listing._meta.get_field("instagram").max_length,
    }
    issues = []
    for name, limit in limits.items():
        if values.get(name) and limit is not None and len(values[name]) > limit:
            issues.append(f"{name} exceeds {limit} characters")
    return issues


def _valid_email(value: str) -> bool:
    try:
        _EMAIL_VALIDATOR(value)
    except ValidationError:
        return False
    return True


def _parse_coordinates(
    latitude_text: str, longitude_text: str
) -> tuple[Decimal | None, Decimal | None, str | None]:
    if latitude_text == "" and longitude_text == "":
        return None, None, None
    if latitude_text == "" or longitude_text == "":
        return (
            None,
            None,
            "latitude and longitude must both be present or both be empty",
        )
    try:
        latitude = Decimal(latitude_text)
        longitude = Decimal(longitude_text)
    except InvalidOperation:
        return None, None, "latitude and longitude must be numbers"
    if not latitude.is_finite() or not longitude.is_finite():
        return None, None, "latitude and longitude must be numbers"
    if latitude == 0 and longitude == 0:
        return None, None, "coordinates 0,0 are invalid"
    if latitude < -90 or latitude > 90 or longitude < -180 or longitude > 180:
        return None, None, "coordinates are out of range"
    return latitude, longitude, None


def _index_existing_listings(index: _KeyIndex) -> None:
    rows = Listing.objects.order_by("id").values(
        "id",
        "import_source_id",
        "phone",
        "website",
        "business_name",
        "title",
        "address",
        "city",
        "state",
        "latitude",
        "longitude",
    )
    for row in rows:
        name = row["business_name"] or row["title"] or ""
        keys = _MatchKeys(
            source_id=_blank_to_none(row["import_source_id"]),
            phone=_blank_to_none(phone_digits(row["phone"] or "")),
            website=_blank_to_none(website_hostname(row["website"] or "")),
            address=address_key(name, row["address"] or "", row["city"] or "", row["state"] or ""),
            coordinates=coordinate_key(
                name, row["city"] or "", row["latitude"], row["longitude"]
            ),
        )
        index.add(keys, f"existing listing {row['id']}")


def _keys_for_prepared(record: PreparedListing) -> _MatchKeys:
    return _MatchKeys(
        source_id=record.source_id,
        phone=_blank_to_none(phone_digits(record.phone)),
        website=_blank_to_none(website_hostname(record.website)),
        address=address_key(
            record.business_name, record.address, record.city, record.state
        ),
        coordinates=coordinate_key(
            record.business_name, record.city, record.latitude, record.longitude
        ),
    )


def _blank_to_none(value: str | None) -> str | None:
    text = (value or "").strip()
    return text or None


def phone_digits(value: str) -> str:
    return re.sub(r"\D+", "", value or "")


def website_hostname(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return ""
    candidate = text if "://" in text else f"http://{text}"
    try:
        host = (urlsplit(candidate).hostname or "").strip().lower()
    except ValueError:
        return ""
    if host.startswith("www."):
        host = host[4:]
    return host


def normalize_match_text(value: str) -> str:
    text = unicodedata.normalize("NFKC", value or "").casefold()
    text = re.sub(r"[^\w\s]", "", text, flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


def address_key(name: str, address: str, city: str, state: str) -> str | None:
    parts = [normalize_match_text(part) for part in (name, address, city, state)]
    if any(not part for part in parts):
        return None
    return "\x1f".join(parts)


def coordinate_key(name: str, city: str, latitude, longitude) -> str | None:
    name_key = normalize_match_text(name)
    city_key = normalize_match_text(city)
    if not name_key or not city_key:
        return None
    latitude_token = round_coord(latitude)
    longitude_token = round_coord(longitude)
    if latitude_token is None or longitude_token is None:
        return None
    if Decimal(latitude_token) == 0 and Decimal(longitude_token) == 0:
        return None
    return "\x1f".join((name_key, city_key, latitude_token, longitude_token))


def round_coord(value) -> str | None:
    if value is None or value == "":
        return None
    try:
        number = value if isinstance(value, Decimal) else Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        return None
    if not number.is_finite():
        return None
    quantized = number.quantize(_FOUR_PLACES, rounding=ROUND_HALF_UP)
    return format(quantized, "f")
