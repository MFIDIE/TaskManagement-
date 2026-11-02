from rest_framework.permissions import BasePermission

class IsManager(BasePermission):
    """Allows access only to authenticated users with the MANAGER role or superusers."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_manager)

class IsManagerOrSelf(BasePermission):
    """Managers have full access; regular employees can only view/edit their own account."""
    def has_object_permission(self, request, view, obj):
        if request.user.is_manager:
            return True
        return obj == request.user