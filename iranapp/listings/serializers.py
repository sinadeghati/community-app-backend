from rest_framework import serializers
from django.utils import timezone
from .models import Listing, ListingImage



class ListingImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ListingImage
        fields = ["id", "image", "image_url", "role", "uploaded_at"]

    def get_image_url(self, obj):
        request = self.context.get("request")
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return None


class ListingSerializer(serializers.ModelSerializer):
    images = serializers.SerializerMethodField()
    posted_days_ago = serializers.SerializerMethodField()
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    business_name = serializers.CharField(read_only=True)
    cover_image = serializers.SerializerMethodField()
    logo = serializers.SerializerMethodField()
    is_verified = serializers.BooleanField(source="verified_badge", read_only=True)

    class Meta:
        model = Listing
        fields = [
            "id",
            "title",
            "business_name",
            "city",
            "state",
            "address",
            "price",
            "description",
            "about",
            "contact_info",
            "phone",
            "website",
            "instagram",
            "category",
            "latitude",
            "longitude",
            "user_id",
            "is_featured",
            "is_sponsored",
            "is_verified",
            "cover_image",
            "logo",
            "created_at",
            "images",
            "posted_days_ago",
        ]

    def get_images(self, obj):
        qs = obj.images.filter(media_status=ListingImage.MediaStatus.ACTIVE)
        return ListingImageSerializer(qs, many=True, context=self.context).data

    def _image_url_for_role(self, obj, role):
        request = self.context.get("request")
        image = obj.images.filter(role=role, media_status=ListingImage.MediaStatus.ACTIVE).first()
        if image and image.image and request:
            return request.build_absolute_uri(image.image.url)
        return None

    def get_cover_image(self, obj):
        return self._image_url_for_role(obj, ListingImage.Role.COVER)

    def get_logo(self, obj):
        return self._image_url_for_role(obj, ListingImage.Role.LOGO)

    def get_posted_days_ago(self, obj):
        if not obj.created_at:
            return None
        return (timezone.now() - obj.created_at).days
