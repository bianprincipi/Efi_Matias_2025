from rest_framework import permissions

class IsAirlineAdmin(permissions.BasePermission):
    """
    Permiso personalizado para permitir el acceso solo a usuarios que son miembros
    del staff (Administradores) y están autenticados (con JWT Token).
    """
    def has_permission(self, request, view):
        # 1. Verificar si el usuario está autenticado (tiene un token JWT válido)
        is_authenticated = request.user and request.user.is_authenticated
        
        # 2. Verificar si el usuario autenticado es miembro del staff (es Admin)
        is_admin_staff = request.user.is_staff if is_authenticated else False
        
        # Devolver True solo si ambas condiciones se cumplen
        return is_authenticated and is_admin_staff