from rest_framework.permissions import BasePermission


class IsStaffManager(BasePermission):
    message = "נדרשת הרשאת מנהל."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_active and request.user.is_staff)


class IsVerifiedOwner(BasePermission):
    message = "נדרש חשבון בעלים מאומת."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated or not request.user.is_active or request.user.is_staff:
            return False
        profile = getattr(request.user, "owner_profile", None)
        return bool(profile and profile.email_verified_at)
