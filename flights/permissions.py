from rest_framework import permissions

class IsAirlineAdmin(permissions.BasePermission):
    """
        Permiso personalizado para permitir el acceso solo a usuarios con rol 'ADMIN'.
        Asume que el modelo de Usuario tiene un campo 'rol'.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.rol == 'ADMIN'