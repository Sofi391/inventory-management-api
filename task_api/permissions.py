from rest_framework.permissions import BasePermission,SAFE_METHODS

class IsManagerOrReadOnly(BasePermission):
    """
    Allow full access to manager group and read-only access to normal users.
    """
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        if request.user.is_staff:
            return True
        return request.user.groups.filter(name='Manager').exists()


class IsManager(BasePermission):
    """
    Allow access only to manager users.
    """
    def has_permission(self, request, view):
        if request.user.is_staff:
            return True
        return request.user.groups.filter(name='Manager').exists()


class IsManagerOrOwner(BasePermission):
    """
    Allow access to manager or sales owners.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff or request.user.groups.filter(name='Manager').exists():
            return True
        return request.user == obj.sold_by


class IsManagerOrTransactionOwner(BasePermission):
    """
    Manager can view all transactions.
    Users can view only their own transactions.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff or request.user.groups.filter(name='Manager').exists():
            return True
        return request.user == obj.created_by

