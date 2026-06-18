from django.contrib import admin

from .models import UserEmailProfile


@admin.register(UserEmailProfile)
class UserEmailProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "email_verified", "email_verified_at")
    list_filter = ("email_verified",)
    search_fields = ("user__username", "user__email")
    readonly_fields = ("email_verified_at",)
