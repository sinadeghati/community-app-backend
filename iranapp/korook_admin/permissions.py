from rest_framework.permissions import BasePermission


class IsKorookStaff(BasePermission):
    """Staff-only access for Korook admin API."""

    message = "Staff access required."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and user.is_staff
        )
