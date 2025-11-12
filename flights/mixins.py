from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect
from django.contrib import messages

class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Mixin que requiere que el usuario esté logueado y sea staff (administrador).
    """
    def test_func(self):
        # El usuario debe ser staff (administrador)
        return self.request.user.is_staff
        
    def handle_no_permission(self):
        # Maneja la redirección y el mensaje si no tiene permisos
        messages.error(self.request, "Acceso denegado. Solo personal autorizado.")
        # Asume que 'flights:index' es tu página principal
        return redirect('flights:index')