from rest_framework import serializers

from .models import BusinessReview


class BusinessReviewSerializer(serializers.ModelSerializer):
    author_username = serializers.CharField(source="author.username", read_only=True)
    author_id = serializers.IntegerField(source="author.id", read_only=True)
    rating = serializers.IntegerField(min_value=1, max_value=5)
    text = serializers.CharField(max_length=2000, trim_whitespace=True)

    class Meta:
        model = BusinessReview
        fields = [
            "id",
            "listing_id",
            "author_username",
            "author_id",
            "rating",
            "text",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "listing_id",
            "author_username",
            "author_id",
            "status",
            "created_at",
            "updated_at",
        ]
