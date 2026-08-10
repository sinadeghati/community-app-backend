import os

from django.contrib.auth.models import User
from rest_framework import serializers

from korook_admin.gallery_order import sort_listing_images
from korook_admin.event_admin_meta import (
    gallery_items,
    read_admin_note_text,
    read_event_meta,
    update_event_fields_from_payload,
    write_event_meta,
)
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
    display_name = serializers.SerializerMethodField()
    businesses_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "display_name",
            "is_active",
            "is_staff",
            "last_login",
            "date_joined",
            "email_verified",
            "role",
            "account_status",
            "admin_note",
            "businesses_count",
        ]

    def _profile(self, obj):
        return getattr(obj, "platform_profile", None)

    def get_display_name(self, obj):
        full_name = f"{obj.first_name} {obj.last_name}".strip()
        return full_name or obj.username

    def get_businesses_count(self, obj):
        created = getattr(obj, "businesses_created_count", None)
        owned = getattr(obj, "businesses_owned_count", None)
        if created is not None or owned is not None:
            return (created or 0) + (owned or 0)
        return None

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
    is_superuser = serializers.BooleanField(read_only=True)
    suspended_at = serializers.SerializerMethodField()
    suspended_by_id = serializers.SerializerMethodField()
    suspended_by_username = serializers.SerializerMethodField()
    events_count = serializers.SerializerMethodField()
    claims_count = serializers.SerializerMethodField()
    reports_count = serializers.SerializerMethodField()

    class Meta(AdminUserListSerializer.Meta):
        fields = AdminUserListSerializer.Meta.fields + [
            "is_superuser",
            "suspended_at",
            "suspended_by_id",
            "suspended_by_username",
            "events_count",
            "claims_count",
            "reports_count",
        ]

    def get_suspended_at(self, obj):
        profile = self._profile(obj)
        return profile.suspended_at if profile else None

    def get_suspended_by_id(self, obj):
        profile = self._profile(obj)
        return profile.suspended_by_id if profile and profile.suspended_by_id else None

    def get_suspended_by_username(self, obj):
        profile = self._profile(obj)
        if profile and profile.suspended_by_id:
            return profile.suspended_by.username
        return None

    def get_events_count(self, obj):
        count = getattr(obj, "events_count", None)
        return count if count is not None else 0

    def get_claims_count(self, obj):
        count = getattr(obj, "claims_count", None)
        return count if count is not None else 0

    def get_reports_count(self, obj):
        count = getattr(obj, "reports_count", None)
        return count if count is not None else 0


class AdminUserBusinessSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Listing
        fields = ["id", "title", "city", "status", "is_featured"]


class AdminUserEventSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ["id", "title", "city", "status", "starts_at", "is_featured"]


class AdminUserClaimSummarySerializer(serializers.ModelSerializer):
    listing_title = serializers.CharField(source="listing.title", read_only=True)

    class Meta:
        model = BusinessClaim
        fields = ["id", "listing", "listing_title", "status", "created_at"]


class AdminUserReportSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentReport
        fields = [
            "id",
            "reported_object_type",
            "reported_object_id",
            "reason",
            "status",
            "created_at",
        ]


class ListingImageAdminSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    filename = serializers.SerializerMethodField()
    file_size = serializers.SerializerMethodField()

    class Meta:
        model = ListingImage
        fields = [
            "id",
            "image",
            "image_url",
            "filename",
            "file_size",
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

    def get_filename(self, obj):
        if not obj.image:
            return ""
        return os.path.basename(obj.image.name)

    def get_file_size(self, obj):
        if not obj.image:
            return None
        try:
            return obj.image.size
        except OSError:
            return None


class ListingAdminSerializer(serializers.ModelSerializer):
    images = serializers.SerializerMethodField()
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

    def get_images(self, obj):
        images = sort_listing_images(obj.images.all(), obj)
        return ListingImageAdminSerializer(
            images, many=True, context=self.context
        ).data


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

class EventAdminListSerializer(serializers.ModelSerializer):
    cover_image_url = serializers.SerializerMethodField()
    listing_title = serializers.SerializerMethodField()
    owner_username = serializers.CharField(source="owner.username", read_only=True)
    organizer_name = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            "id",
            "title",
            "cover_image_url",
            "listing_id",
            "listing_title",
            "owner_id",
            "owner_username",
            "organizer",
            "organizer_name",
            "category",
            "city",
            "starts_at",
            "ends_at",
            "status",
            "is_featured",
            "created_at",
            "updated_at",
        ]

    def get_cover_image_url(self, obj):
        request = self.context.get("request")
        if obj.cover_image and request:
            return request.build_absolute_uri(obj.cover_image.url)
        return None

    def get_listing_title(self, obj):
        return obj.listing.title if obj.listing_id else None

    def get_organizer_name(self, obj):
        if obj.organizer:
            return obj.organizer
        return obj.owner.username if obj.owner_id else ""


class EventAdminSerializer(serializers.ModelSerializer):
    owner_id = serializers.IntegerField(source="owner.id", read_only=True)
    owner_username = serializers.CharField(source="owner.username", read_only=True)
    listing_id = serializers.IntegerField(allow_null=True, required=False)
    listing_title = serializers.SerializerMethodField()
    cover_image_url = serializers.SerializerMethodField()
    tags = serializers.ListField(child=serializers.CharField(), required=False)
    phone = serializers.CharField(required=False, allow_blank=True)
    website = serializers.CharField(required=False, allow_blank=True)
    instagram = serializers.CharField(required=False, allow_blank=True)
    visibility = serializers.SerializerMethodField()
    gallery = serializers.SerializerMethodField()
    media_count = serializers.SerializerMethodField()
    promotions_count = serializers.SerializerMethodField()
    reports_count = serializers.SerializerMethodField()
    claims_count = serializers.SerializerMethodField()
    admin_note_text = serializers.SerializerMethodField()

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
            "listing_title",
            "owner_id",
            "owner_username",
            "status",
            "is_featured",
            "is_sponsored",
            "display_priority",
            "cover_image",
            "cover_image_url",
            "cover_media_status",
            "cover_moderation_reason",
            "admin_note",
            "admin_note_text",
            "tags",
            "phone",
            "website",
            "instagram",
            "visibility",
            "gallery",
            "media_count",
            "promotions_count",
            "reports_count",
            "claims_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def get_cover_image_url(self, obj):
        request = self.context.get("request")
        if obj.cover_image and request:
            return request.build_absolute_uri(obj.cover_image.url)
        return None

    def get_listing_title(self, obj):
        return obj.listing.title if obj.listing_id else None

    def get_visibility(self, obj):
        if obj.status == Event.Status.PUBLISHED:
            return "public"
        if obj.status == Event.Status.HIDDEN:
            return "hidden"
        return "draft"

    def get_gallery(self, obj):
        request = self.context.get("request")
        items = []
        for item in gallery_items(obj):
            storage_path = item.get("storage_path")
            image_url = None
            if storage_path and request:
                from django.core.files.storage import default_storage

                if default_storage.exists(storage_path):
                    image_url = request.build_absolute_uri(default_storage.url(storage_path))
            items.append({**item, "image_url": image_url})
        return items

    def get_media_count(self, obj):
        return (1 if obj.cover_image else 0) + len(gallery_items(obj))

    def get_promotions_count(self, obj):
        count = getattr(obj, "promotions_count", None)
        return count if count is not None else obj.promotions.count()

    def get_reports_count(self, obj):
        count = getattr(obj, "reports_count", None)
        return count if count is not None else obj.content_reports.count()

    def get_claims_count(self, obj):
        if not obj.listing_id:
            return 0
        return obj.listing.claims.count()

    def get_admin_note_text(self, obj):
        return read_admin_note_text(obj)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        meta = read_event_meta(instance)
        contact = meta.get("contact", {})
        data["tags"] = meta.get("tags", [])
        data["phone"] = contact.get("phone", "")
        data["website"] = contact.get("website", "")
        data["instagram"] = contact.get("instagram", "")
        return data

    def update(self, instance, validated_data):
        tags = validated_data.pop("tags", None)
        phone = validated_data.pop("phone", None)
        website = validated_data.pop("website", None)
        instagram = validated_data.pop("instagram", None)
        admin_note_text = self.initial_data.get("admin_note_text")

        visibility = self.initial_data.get("visibility")
        if visibility == "public":
            validated_data["status"] = Event.Status.PUBLISHED
        elif visibility == "hidden":
            validated_data["status"] = Event.Status.HIDDEN
        elif visibility == "draft":
            validated_data["status"] = Event.Status.DRAFT

        listing_id = validated_data.pop("listing_id", None)
        if listing_id is not None:
            from listings.models import Listing

            instance.listing = Listing.objects.filter(pk=listing_id).first()
        elif "listing_id" in self.initial_data and self.initial_data.get("listing_id") in ("", None):
            instance.listing = None

        instance = super().update(instance, validated_data)

        payload = {}
        if tags is not None:
            payload["tags"] = tags
        if phone is not None:
            payload["phone"] = phone
        if website is not None:
            payload["website"] = website
        if instagram is not None:
            payload["instagram"] = instagram
        if payload:
            update_event_fields_from_payload(instance, payload)

        if admin_note_text is not None:
            meta = read_event_meta(instance)
            write_event_meta(instance, meta, str(admin_note_text))

        return instance

    def create(self, validated_data):
        tags = validated_data.pop("tags", None)
        phone = validated_data.pop("phone", None)
        website = validated_data.pop("website", None)
        instagram = validated_data.pop("instagram", None)
        listing_id = validated_data.pop("listing_id", None)
        validated_data.pop("visibility", None)

        if listing_id:
            from listings.models import Listing

            validated_data["listing"] = Listing.objects.filter(pk=listing_id).first()

        instance = super().create(validated_data)
        payload = {}
        if tags is not None:
            payload["tags"] = tags
        if phone is not None:
            payload["phone"] = phone
        if website is not None:
            payload["website"] = website
        if instagram is not None:
            payload["instagram"] = instagram
        if payload:
            update_event_fields_from_payload(instance, payload)
        return instance


class PromotionAdminListSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    destination_type = serializers.SerializerMethodField()
    destination_label = serializers.SerializerMethodField()

    class Meta:
        model = Promotion
        fields = [
            "id",
            "title",
            "image_url",
            "placement",
            "advertiser_name",
            "status",
            "display_priority",
            "starts_at",
            "ends_at",
            "destination_type",
            "destination_label",
            "is_active",
            "hero_approved",
            "created_at",
            "updated_at",
        ]

    def get_image_url(self, obj):
        request = self.context.get("request")
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return None

    def get_destination_type(self, obj):
        return _promotion_destination_type(obj)

    def get_destination_label(self, obj):
        return _promotion_destination_label(obj)


def _promotion_destination_type(promo) -> str:
    if promo.listing_id:
        return "business"
    if promo.event_id:
        return "event"
    if promo.cta_link:
        return "external_url"
    if promo.target_route:
        return "internal"
    return "none"


def _promotion_destination_label(promo) -> str:
    if promo.listing_id and promo.listing:
        return promo.listing.title
    if promo.event_id and promo.event:
        return promo.event.title
    if promo.cta_link:
        return promo.cta_link
    if promo.target_route:
        suffix = f" ({promo.target_id})" if promo.target_id else ""
        return f"{promo.target_route}{suffix}"
    return "No destination"


class PromotionAdminSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    image_filename = serializers.SerializerMethodField()
    listing_id = serializers.IntegerField(allow_null=True, required=False)
    event_id = serializers.IntegerField(allow_null=True, required=False)
    listing_title = serializers.SerializerMethodField()
    event_title = serializers.SerializerMethodField()
    destination_type = serializers.CharField(required=False, allow_blank=True)
    destination_label = serializers.SerializerMethodField()
    schedule_state = serializers.SerializerMethodField()
    analytics_available = serializers.SerializerMethodField()

    class Meta:
        model = Promotion
        fields = [
            "id",
            "advertiser_name",
            "listing_id",
            "listing_title",
            "event_id",
            "event_title",
            "placement",
            "title",
            "subtitle",
            "image",
            "image_url",
            "image_filename",
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
            "destination_type",
            "destination_label",
            "schedule_state",
            "analytics_available",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at", "status"]

    def get_image_url(self, obj):
        request = self.context.get("request")
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return None

    def get_image_filename(self, obj):
        if not obj.image:
            return ""
        import os

        return os.path.basename(obj.image.name)

    def get_listing_title(self, obj):
        return obj.listing.title if obj.listing_id and obj.listing else None

    def get_event_title(self, obj):
        return obj.event.title if obj.event_id and obj.event else None

    def get_destination_label(self, obj):
        return _promotion_destination_label(obj)

    def get_schedule_state(self, obj):
        return obj.status

    def get_analytics_available(self, obj):
        return False

    def validate(self, attrs):
        starts = attrs.get("starts_at")
        ends = attrs.get("ends_at")
        if self.instance:
            if starts is None:
                starts = self.instance.starts_at
            if ends is None:
                ends = self.instance.ends_at
        if starts and ends and ends < starts:
            raise serializers.ValidationError(
                {"ends_at": ["End date must be after start date."]}
            )
        cta_link = attrs.get("cta_link")
        if cta_link is None and self.instance:
            cta_link = self.instance.cta_link
        if cta_link and not str(cta_link).startswith(("http://", "https://")):
            raise serializers.ValidationError(
                {"cta_link": ["Enter a valid URL starting with http:// or https://"]}
            )
        return attrs

    def _apply_destination_type(self, instance, destination_type):
        if not destination_type:
            return
        if destination_type == "business":
            instance.cta_link = ""
            instance.target_route = ""
            instance.target_id = ""
            instance.event = None
        elif destination_type == "event":
            instance.cta_link = ""
            instance.target_route = ""
            instance.target_id = ""
            instance.listing = None
        elif destination_type == "external_url":
            instance.listing = None
            instance.event = None
            instance.target_route = ""
            instance.target_id = ""
        elif destination_type == "internal":
            instance.listing = None
            instance.event = None
            instance.cta_link = ""
        elif destination_type == "none":
            instance.listing = None
            instance.event = None
            instance.cta_link = ""
            instance.target_route = ""
            instance.target_id = ""

    def create(self, validated_data):
        destination_type = validated_data.pop("destination_type", None)
        listing_id = validated_data.pop("listing_id", None)
        event_id = validated_data.pop("event_id", None)
        instance = super().create(validated_data)
        if listing_id is not None:
            from listings.models import Listing

            instance.listing = Listing.objects.filter(pk=listing_id).first()
        if event_id is not None:
            from korook_platform.models import Event

            instance.event = Event.objects.filter(pk=event_id).first()
        self._apply_destination_type(instance, destination_type)
        instance.save()
        return instance

    def update(self, instance, validated_data):
        destination_type = validated_data.pop("destination_type", None)
        listing_id = validated_data.pop("listing_id", None)
        event_id = validated_data.pop("event_id", None)
        instance = super().update(instance, validated_data)
        if listing_id is not None:
            from listings.models import Listing

            instance.listing = Listing.objects.filter(pk=listing_id).first() if listing_id else None
        if event_id is not None:
            from korook_platform.models import Event

            instance.event = Event.objects.filter(pk=event_id).first() if event_id else None
        if destination_type is not None:
            self._apply_destination_type(instance, destination_type)
        instance.save()
        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["destination_type"] = _promotion_destination_type(instance)
        return data


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
