from rest_framework import serializers
from django.utils import timezone
from .models import Listing, ListingImage


class ListingImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ListingImage
        fields = ["id","image", "image_url", "uploaded_at"]

    def get_image_url(self, obj):
        request = self.context.get("request")
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return None


class ListingSerializer(serializers.ModelSerializer):
    images = ListingImageSerializer(many=True, read_only=True)
    posted_days_ago = serializers.SerializerMethodField()

    class Meta:
        model = Listing
        fields = [
            "id",
            "title",
            "city",
            "state",
            "price",
            "description",
            "contact_info",
            "created_at",
            "images",
            "posted_days_ago",
        ]

    def get_posted_days_ago(self, obj):
        if not obj.created_at:
            return None
        return (timezone.now() - obj.created_at).days
