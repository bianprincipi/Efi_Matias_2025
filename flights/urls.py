from django.urls import path, include
from rest_framework.routers import DefaultRouter
from django.views.generic import TemplateView  # CAMBIO: para exponer login dentro del app
from . import views

# Router DRF → expone /flights/api/<recurso>/
router = DefaultRouter()
router.register(r'vuelos', views.VueloViewSet, basename='vuelo')
router.register(r'pasajeros', views.PassengerViewSet, basename='pasajero')
router.register(r'reservas', views.ReservationViewSet, basename='reserva')
router.register(r'aviones', views.AircraftViewSet, basename='avion')
router.register(r'boletos', views.TicketViewSet, basename='boleto')

app_name = 'flights'

urlpatterns = [
    # ===============================
    # HTML (server-rendered)
    # ===============================
    path('', views.index, name='index'),

    # Búsqueda HTML (si la usás aparte del index)
    path('search/', views.search_flights, name='search_flights'),

    # Dashboard / gestión (HTML)
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('dashboard/vuelos/', views.manage_flights, name='manage_flights'),
    path('dashboard/vuelos/crear/', views.create_flight, name='create_flight'),
    path('dashboard/vuelos/editar/<int:flight_id>/', views.edit_flight, name='edit_flight'),
    path('dashboard/vuelos/eliminar/<int:flight_id>/', views.delete_flight, name='delete_flight'),

    path('dashboard/reservas/', views.manage_reservations, name='manage_reservations'),
    path('dashboard/aviones/', views.manage_aircrafts, name='manage_aircrafts'),
    path('dashboard/pasajeros/', views.manage_passengers, name='manage_passengers'),
    path('dashboard/usuarios/', views.manage_users, name='manage_users'),

    # Detalles HTML
    path('<int:flight_id>/', views.flight_detail, name='flight_detail'),
    path('passenger/<int:passenger_id>/', views.passenger_detail, name='passenger_detail'),
    path('reservation/<int:reservation_id>/', views.reservation_detail, name='reservation_detail'),
    path('ticket/<int:ticket_id>/', views.ticket_detail, name='ticket_detail'),

    # Página HTML: Mis reservas (cliente)
    path('mis-reservas/', views.my_reservations, name='my_reservations'),

    # CAMBIO: Alias de login dentro del namespace `flights`
    # Esto permite usar `{% url 'flights:login' %}` en templates (redirige a la misma plantilla login.html).
    path('login/', TemplateView.as_view(template_name='login.html'), name='login'),  # CAMBIO

    # ===============================
    # APIs (DRF)
    # ===============================

    # Endpoint de búsqueda pública (API)
    path('api/vuelos/buscar/', views.SearchFlightsAPIView.as_view(), name='flight-search-api'),

    # Endpoint de perfil (API)
    path('api/profile/', views.UserProfileAPIView.as_view(), name='api_profile'),

    # CRUDs generados por el router: /flights/api/<recurso>/
    path('api/', include(router.urls)),
]
