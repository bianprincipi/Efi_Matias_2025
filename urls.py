from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.views.generic.base import RedirectView

# Importación necesaria para cargar solo la plantilla HTML
from django.views.generic import TemplateView

schema_view = get_schema_view(
    openapi.Info(
        title="API Sistema de Gestion de Aerolinea (EFI)",
        default_version='v1',
        description="Documentacion de la API REST para la gestion de vuelos, reservas, pasajeros y boletos.",
        contact=openapi.Contact(email="email_ej@example.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
    url='http://127.0.0.1:8000/flights/'
)

urlpatterns = [
    path('', RedirectView.as_view(url='flights/', permanent=True), name='index_redirect'),
    path('admin/', admin.site.urls),

    # conecta las urls de la aplicacion fligths
    path('flights/', include(('flights.urls', 'flights'), namespace='flights')),

    # RUTA DE LOGIN CORREGIDA: Simplemente carga la plantilla login.html.
    # El JavaScript dentro de esa plantilla manejará la autenticación JWT.
    path('login/', TemplateView.as_view(template_name='login.html'), name='login'),
    

    path('api/v1/', include('flights.api.urls')),
    # El logout se maneja completamente en el frontend (base.html) eliminando el token.
    # Dejamos esta ruta solo si tienes otra lógica de backend que necesite limpiarse:
    # path('logout/', auth_views.LogoutView.as_view(next_page='/flights/'), name='logout'), 

    # endpoints de autenticacion jwt (ESTOS SON LOS QUE USA EL JAVASCRIPT)
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # rutas de documentacion swagger/redoc
    path('swagger<format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'), 
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]