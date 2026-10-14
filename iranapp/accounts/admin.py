from django.contrib import admin

from .models import ExternalIdentity, UserEmailProfile


@admin.register(UserEmailProfile)
class UserEmailProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "email_verified", "email_verified_at")
    list_filter = ("email_verified",)
    search_fields = ("user__username", "user__email")
    readonly_fields = ("email_verified_at",)


@admin.register(ExternalIdentity)
class ExternalIdentityAdmin(admin.ModelAdmin):
    list_display = ("user", "provider", "provider_subject", "provider_email", "updated_at")
    list_filter = ("provider",)
    search_fields = ("provider_subject", "provider_email", "user__username", "user__email")
