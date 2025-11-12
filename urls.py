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
from django.views.generic import TemplateView  # (OK) login con template plano

# Swagger apuntando al prefijo /flights/ (tus APIs están montadas ahí)
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
    # CAMBIO: redirección por NOMBRE de ruta (namespace 'flights'), en lugar de URL fija
    path('', RedirectView.as_view(pattern_name='flights:index', permanent=False), name='index_redirect'),  # CAMBIO

    path('admin/', admin.site.urls),

    # CAMBIO: incluye el app con namespace 'flights' (habilita {% url 'flights:...' %})
    path('flights/', include(('flights.urls', 'flights'), namespace='flights')),  # CAMBIO

    # Login de cara al front (tu index usa /login/). Sirve solo la plantilla; el JS maneja JWT.
    path('login/', TemplateView.as_view(template_name='login.html'), name='login'),

    # Endpoints JWT
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Swagger / Redoc
    path('swagger<format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]
