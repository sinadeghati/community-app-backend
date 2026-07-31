from django.contrib import admin

from .models import (
    AdminAuditLog,
    BusinessClaim,
    ContentReport,
    Event,
    Promotion,
    UserPlatformProfile,
)


@admin.register(UserPlatformProfile)
class UserPlatformProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "account_status", "created_at")
    list_filter = ("role", "account_status")
    search_fields = ("user__username", "user__email")
    raw_id_fields = ("user", "suspended_by")


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "starts_at", "owner", "is_featured")
    list_filter = ("status", "is_featured", "is_sponsored")
    search_fields = ("title", "organizer", "city")
    raw_id_fields = ("owner", "listing")


@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "placement",
        "status",
        "is_active",
        "display_priority",
        "starts_at",
        "ends_at",
    )
    list_filter = ("placement", "status", "is_active")
    search_fields = ("title", "advertiser_name")
    raw_id_fields = ("listing", "event")


@admin.register(BusinessClaim)
class BusinessClaimAdmin(admin.ModelAdmin):
    list_display = ("id", "listing", "requester", "status", "created_at")
    list_filter = ("status",)
    raw_id_fields = ("listing", "requester", "reviewed_by")


@admin.register(ContentReport)
class ContentReportAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "reported_object_type",
        "reported_object_id",
        "status",
        "reason",
        "created_at",
    )
    list_filter = ("status", "reported_object_type", "reason")
    raw_id_fields = ("reported_by", "reviewed_by", "reported_user", "listing", "event")


@admin.register(AdminAuditLog)
class AdminAuditLogAdmin(admin.ModelAdmin):
    list_display = ("action_type", "object_type", "object_id", "actor", "created_at")
    list_filter = ("action_type", "object_type")
    search_fields = ("summary",)
    raw_id_fields = ("actor",)
    readonly_fields = (
        "actor",
        "action_type",
        "object_type",
        "object_id",
        "summary",
        "before_state",
        "after_state",
        "admin_note",
        "created_at",
    )
