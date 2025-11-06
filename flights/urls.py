from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views 
from .views import (
    VueloViewSet, 
    PassengerViewSet, 
    ReservationViewSet, 
    AircraftViewSet,
    TicketViewSet
) 
from rest_framework import routers

router = DefaultRouter()
router.register(r'vuelos', VueloViewSet, basename='vuelo')         # /api/vuelos/
router.register(r'pasajeros', PassengerViewSet, basename='pasajero') # /api/pasajeros/
router.register(r'reservas', ReservationViewSet, basename='reserva') # /api/reservas/
router.register(r'aviones', AircraftViewSet, basename='avion')     # /api/aviones/
router.register(r'boletos', TicketViewSet, basename='boleto')     # /api/boletos/

app_name = 'flights'

urlpatterns = [
    
    # HOME PAGE (Muestra Cliente o redirige a Admin Dashboard si es staff)
    path('', views.index, name='index'),
    
    # BÚSQUEDA WEB
    path('search/', views.search_flights, name='search_flights'),
    
    # DASHBOARD DE ADMINISTRADOR WEB
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    
    # RUTAS DE DETALLE WEB (Correctas sin el prefijo 'flights/')
    path('<int:flight_id>/', views.flight_detail, name='flight_detail'), # Detalle de Vuelo (Ej: /flights/42/)
    path('passenger/<int:passenger_id>/', views.passenger_detail, name='passenger_detail'),
    path('reservation/<int:reservation_id>/', views.reservation_detail, name='reservation_detail'),
    path('ticket/<int:ticket_id>/', views.ticket_detail, name='ticket_detail'),

    # RUTAS API REST
    path('api/', include(router.urls)), 
]