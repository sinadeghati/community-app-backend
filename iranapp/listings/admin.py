from django.contrib import admin

from .models import Listing, ListingImage


class ListingImageInline(admin.TabularInline):
    model = ListingImage
    extra = 0
    fields = ("image", "role", "media_status", "uploaded_at")
    readonly_fields = ("uploaded_at",)


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "status",
        "city",
        "is_featured",
        "is_sponsored",
        "premium_status",
        "verified_badge",
        "user",
    )
    list_filter = ("status", "is_featured", "is_sponsored", "premium_status", "category")
    search_fields = ("title", "business_name", "city", "contact_info")
    raw_id_fields = ("user", "owner")
    inlines = [ListingImageInline]


@admin.register(ListingImage)
class ListingImageAdmin(admin.ModelAdmin):
    list_display = ("listing", "role", "media_status", "uploaded_at")
    list_filter = ("role", "media_status")
    raw_id_fields = ("listing", "uploaded_by", "reviewed_by")
