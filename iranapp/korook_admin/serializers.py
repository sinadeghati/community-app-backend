from django.contrib.auth.models import User
from rest_framework import serializers

from accounts.models import UserEmailProfile
from listings.models import Listing, ListingImage
from korook_platform.models import (
    AdminAuditLog,
    BusinessClaim,
    ContentReport,
    Event,
    Promotion,
    UserPlatformProfile,
)


class AdminUserListSerializer(serializers.ModelSerializer):
    email_verified = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    account_status = serializers.SerializerMethodField()
    admin_note = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "is_active",
            "is_staff",
            "last_login",
            "date_joined",
            "email_verified",
            "role",
            "account_status",
            "admin_note",
        ]

    def _profile(self, obj):
        return getattr(obj, "platform_profile", None)

    def get_email_verified(self, obj):
        try:
            return obj.email_profile.email_verified
        except UserEmailProfile.DoesNotExist:
            return False

    def get_role(self, obj):
        profile = self._profile(obj)
        return profile.role if profile else UserPlatformProfile.Role.USER

    def get_account_status(self, obj):
        profile = self._profile(obj)
        return profile.account_status if profile else UserPlatformProfile.AccountStatus.ACTIVE

    def get_admin_note(self, obj):
        profile = self._profile(obj)
        return profile.admin_note if profile else ""


class AdminUserDetailSerializer(AdminUserListSerializer):
    pass


class ListingImageAdminSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ListingImage
        fields = [
            "id",
            "image",
            "image_url",
            "role",
            "media_status",
            "moderation_reason",
            "uploaded_at",
            "reviewed_at",
        ]
        read_only_fields = ["uploaded_at", "reviewed_at"]

    def get_image_url(self, obj):
        request = self.context.get("request")
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return None


class ListingAdminSerializer(serializers.ModelSerializer):
    images = ListingImageAdminSerializer(many=True, read_only=True)
    owner_id = serializers.IntegerField(source="owner.id", read_only=True, allow_null=True)
    user_id = serializers.IntegerField(source="user.id", read_only=True)

    class Meta:
        model = Listing
        fields = [
            "id",
            "user_id",
            "owner_id",
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
            "status",
            "is_featured",
            "is_sponsored",
            "premium_status",
            "premium_start_date",
            "premium_end_date",
            "display_priority",
            "verified_badge",
            "verified_at",
            "admin_note",
            "created_at",
            "updated_at",
            "images",
        ]
        read_only_fields = ["created_at", "updated_at", "verified_at"]


class ListingAdminListSerializer(serializers.ModelSerializer):
    """Lightweight row for admin business list (no nested image galleries)."""

    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = Listing
        fields = [
            "id",
            "title",
            "business_name",
            "city",
            "status",
            "is_featured",
            "thumbnail_url",
        ]

    def get_thumbnail_url(self, obj):
        thumbnail_name = getattr(obj, "thumbnail_image", None)
        if not thumbnail_name:
            return None
        request = self.context.get("request")
        if not request:
            return None
        from django.core.files.storage import default_storage

        return request.build_absolute_uri(default_storage.url(thumbnail_name))

class EventAdminSerializer(serializers.ModelSerializer):
    owner_id = serializers.IntegerField(source="owner.id", read_only=True)
    listing_id = serializers.IntegerField(source="listing.id", read_only=True, allow_null=True)
    cover_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            "id",
            "title",
            "description",
            "category",
            "starts_at",
            "ends_at",
            "location",
            "address",
            "city",
            "state",
            "zip_code",
            "country",
            "latitude",
            "longitude",
            "organizer",
            "ticket_url",
            "ticket_provider_label",
            "listing_id",
            "owner_id",
            "status",
            "is_featured",
            "is_sponsored",
            "display_priority",
            "cover_image",
            "cover_image_url",
            "cover_media_status",
            "cover_moderation_reason",
            "admin_note",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def get_cover_image_url(self, obj):
        request = self.context.get("request")
        if obj.cover_image and request:
            return request.build_absolute_uri(obj.cover_image.url)
        return None


class PromotionAdminSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Promotion
        fields = [
            "id",
            "advertiser_name",
            "listing",
            "event",
            "placement",
            "title",
            "subtitle",
            "image",
            "image_url",
            "video_url",
            "cta_text",
            "cta_link",
            "target_route",
            "target_id",
            "channel",
            "starts_at",
            "ends_at",
            "is_active",
            "display_priority",
            "sponsored_label",
            "status",
            "hero_approved",
            "admin_note",
            "billing_reference",
            "campaign_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at", "status"]

    def get_image_url(self, obj):
        request = self.context.get("request")
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return None


class BusinessClaimAdminSerializer(serializers.ModelSerializer):
    listing_title = serializers.CharField(source="listing.title", read_only=True)
    requester_username = serializers.CharField(source="requester.username", read_only=True)
    requester_email = serializers.CharField(source="requester.email", read_only=True)

    class Meta:
        model = BusinessClaim
        fields = [
            "id",
            "listing",
            "listing_title",
            "requester",
            "requester_username",
            "requester_email",
            "status",
            "admin_note",
            "reviewed_by",
            "reviewed_at",
            "created_at",
        ]
        read_only_fields = ["reviewed_by", "reviewed_at", "created_at"]


class ContentReportAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentReport
        fields = [
            "id",
            "reported_object_type",
            "reported_object_id",
            "reported_user",
            "listing",
            "event",
            "listing_image",
            "reason",
            "description",
            "reported_by",
            "status",
            "reviewed_by",
            "reviewed_at",
            "admin_note",
            "action_taken",
            "created_at",
        ]
        read_only_fields = ["reviewed_by", "reviewed_at", "created_at"]


class AdminAuditLogSerializer(serializers.ModelSerializer):
    actor_username = serializers.CharField(source="actor.username", read_only=True)

    class Meta:
        model = AdminAuditLog
        fields = [
            "id",
            "actor",
            "actor_username",
            "action_type",
            "object_type",
            "object_id",
            "summary",
            "before_state",
            "after_state",
            "admin_note",
            "created_at",
        ]
