import os

from rest_framework.exceptions import ValidationError

ALLOWED_IMAGE_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def validate_image_upload(uploaded_file):
    if not uploaded_file:
        raise ValidationError({"image": ["Image file is required."]})

    content_type = getattr(uploaded_file, "content_type", "") or ""
    filename = getattr(uploaded_file, "name", "") or ""
    extension = os.path.splitext(filename)[1].lower()

    if content_type not in ALLOWED_IMAGE_CONTENT_TYPES and extension not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError(
            {
                "image": [
                    "Unsupported image format. Please upload a PNG, JPEG, or WEBP file."
                ]
            }
        )

    return uploaded_file
