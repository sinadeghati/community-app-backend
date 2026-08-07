import json

from listings.models import ListingImage

GALLERY_ORDER_PREFIX = "__korook_gallery_order__:"


def read_gallery_order(listing) -> list[int]:
    value = (listing.gallery_urls or "").strip()
    if not value.startswith(GALLERY_ORDER_PREFIX):
        return []
    try:
        payload = json.loads(value[len(GALLERY_ORDER_PREFIX) :])
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, list):
        return []
    return [int(item) for item in payload if str(item).isdigit()]


def write_gallery_order(listing, order_ids: list[int]) -> None:
    listing.gallery_urls = GALLERY_ORDER_PREFIX + json.dumps(order_ids)
    listing.save(update_fields=["gallery_urls", "updated_at"])


def sort_listing_images(images, listing):
    images = list(images)
    gallery_order = read_gallery_order(listing)
    if not gallery_order:
        return sorted(images, key=lambda image: (image.role, image.id))

    order_map = {image_id: index for index, image_id in enumerate(gallery_order)}

    def sort_key(image):
        if image.role == ListingImage.Role.COVER:
            return (0, 0)
        if image.role == ListingImage.Role.LOGO:
            return (1, 0)
        return (2, order_map.get(image.id, 10_000 + image.id))

    return sorted(images, key=sort_key)
