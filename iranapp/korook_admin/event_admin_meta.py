import json
import uuid
from copy import deepcopy

META_PREFIX = "__korook_event_meta__:"
META_SEPARATOR = "\n\n---\n\n"


def _default_meta() -> dict:
    return {
        "tags": [],
        "contact": {"phone": "", "website": "", "instagram": ""},
        "gallery": [],
    }


def parse_admin_note(admin_note: str) -> tuple[dict, str]:
    value = admin_note or ""
    if not value.startswith(META_PREFIX):
        return _default_meta(), value

    payload, _, note = value[len(META_PREFIX) :].partition(META_SEPARATOR)
    try:
        meta = json.loads(payload)
    except json.JSONDecodeError:
        return _default_meta(), value

    if not isinstance(meta, dict):
        return _default_meta(), note

    merged = _default_meta()
    merged.update({key: meta.get(key, merged[key]) for key in merged})
    if not isinstance(merged.get("tags"), list):
        merged["tags"] = []
    contact = merged.get("contact")
    if not isinstance(contact, dict):
        merged["contact"] = _default_meta()["contact"]
    else:
        merged["contact"] = {
            "phone": contact.get("phone", "") or "",
            "website": contact.get("website", "") or "",
            "instagram": contact.get("instagram", "") or "",
        }
    gallery = merged.get("gallery")
    if not isinstance(gallery, list):
        merged["gallery"] = []
    return merged, note


def serialize_admin_note(meta: dict, note: str = "") -> str:
    payload = json.dumps(meta, separators=(",", ":"))
    if note.strip():
        return f"{META_PREFIX}{payload}{META_SEPARATOR}{note.strip()}"
    return f"{META_PREFIX}{payload}"


def read_event_meta(event) -> dict:
    meta, _ = parse_admin_note(event.admin_note or "")
    return meta


def read_admin_note_text(event) -> str:
    _, note = parse_admin_note(event.admin_note or "")
    return note


def write_event_meta(event, meta: dict, note: str | None = None) -> None:
    if note is None:
        _, note = parse_admin_note(event.admin_note or "")
    event.admin_note = serialize_admin_note(meta, note)
    event.save(update_fields=["admin_note", "updated_at"])


def gallery_items(event) -> list[dict]:
    return list(read_event_meta(event).get("gallery", []))


def add_gallery_item(event, storage_path: str, filename: str) -> dict:
    meta = read_event_meta(event)
    item = {
        "id": str(uuid.uuid4()),
        "storage_path": storage_path,
        "filename": filename,
        "uploaded_at": "",
    }
    meta["gallery"].append(item)
    write_event_meta(event, meta)
    return item


def remove_gallery_item(event, image_id: str) -> dict | None:
    meta = read_event_meta(event)
    gallery = meta.get("gallery", [])
    target = next((item for item in gallery if item.get("id") == image_id), None)
    if not target:
        return None
    meta["gallery"] = [item for item in gallery if item.get("id") != image_id]
    write_event_meta(event, meta)
    return target


def reorder_gallery(event, order_ids: list[str]) -> list[dict]:
    meta = read_event_meta(event)
    gallery = meta.get("gallery", [])
    order_map = {item.get("id"): index for index, item in enumerate(gallery)}
    sorted_items = sorted(
        gallery,
        key=lambda item: (
            order_ids.index(item["id"])
            if item.get("id") in order_ids
            else 10_000 + order_map.get(item.get("id"), 0)
        ),
    )
    meta["gallery"] = sorted_items
    write_event_meta(event, meta)
    return sorted_items


def update_event_fields_from_payload(event, data: dict) -> None:
    meta = read_event_meta(event)
    changed = False

    if "tags" in data:
        tags = data.get("tags") or []
        if isinstance(tags, str):
            tags = [part.strip() for part in tags.split(",") if part.strip()]
        meta["tags"] = [str(tag) for tag in tags if str(tag).strip()]
        changed = True

    contact_fields = ("phone", "website", "instagram")
    if any(field in data for field in contact_fields):
        contact = deepcopy(meta.get("contact", _default_meta()["contact"]))
        for field in contact_fields:
            if field in data:
                contact[field] = data.get(field) or ""
        meta["contact"] = contact
        changed = True

    if changed:
        write_event_meta(event, meta)
