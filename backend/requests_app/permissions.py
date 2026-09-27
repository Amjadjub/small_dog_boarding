from rest_framework.permissions import BasePermission


class IsStaffManager(BasePermission):
    message = "נדרשת הרשאת מנהל."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_active and request.user.is_staff)
