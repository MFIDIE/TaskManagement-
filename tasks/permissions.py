from rest_framework.permissions import BasePermission

class IsManagerOrAssignee(BasePermission):
    """
    Managers have full permissions to create, view, edit, and delete tasks.
    Employees can only view and update tasks assigned to them.
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        
        # Managers can do anything
        if request.user.is_manager:
            return True
        
        # Employees cannot create or delete tasks
        if view.action in ['create', 'destroy']:
            return False
            
        return True

    def has_object_permission(self, request, view, obj):
        if request.user.is_manager:
            return True
        # Employees can only access tasks assigned directly to them
        return obj.assigned_to == request.user