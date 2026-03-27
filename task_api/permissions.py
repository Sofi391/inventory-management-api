from rest_framework.permissions import BasePermission, SAFE_METHODS

MANAGER_GROUP = 'Manager'


def _is_manager(user):
    return user.is_staff or user.groups.filter(name=MANAGER_GROUP).exists()


class IsManagerOrReadOnly(BasePermission):
    """
    Authenticated managers get full access.
    Authenticated non-managers get read-only access.
    Unauthenticated users are denied.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return _is_manager(request.user)


class IsManager(BasePermission):
    """
    Allow access only to authenticated manager users.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return _is_manager(request.user)


class IsManagerOrOwner(BasePermission):
    """
    Managers get full access.
    Authenticated non-managers can only create and access their own objects.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if _is_manager(request.user):
            return True
        return request.method in SAFE_METHODS or request.method == 'POST'

    def has_object_permission(self, request, view, obj):
        if _is_manager(request.user):
            return True
        return request.user == obj.sold_by


class IsManagerOrTransactionOwner(BasePermission):
    """
    Managers can view all transactions.
    Authenticated non-managers can only view their own transactions.
    Data filtering is enforced in get_queryset on list views.
    has_object_permission is reserved for future detail views.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return True

    def has_object_permission(self, request, view, obj):
        if _is_manager(request.user):
            return True
        return request.user == obj.created_by

