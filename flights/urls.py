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

router = DefaultRouter()
router.register(r'vuelos', VueloViewSet, basename='vuelo')         # /api/vuelos/
router.register(r'pasajeros', PassengerViewSet, basename='pasajero') # /api/pasajeros/
router.register(r'reservas', ReservationViewSet, basename='reserva') # /api/reservas/
router.register(r'aviones', AircraftViewSet, basename='avion')     # /api/aviones/
router.register(r'boletos', TicketViewSet, basename='boleto')     # /api/boletos/

urlpatterns = [
    
    # Ruta /flights/
    path('', views.index, name='flight_index'),
    
    # Ruta /flights/search/
    path('search/', views.search_flights, name='search_flights'),
    
    # Rutas de detalle web
    path('<int:flight_id>/', views.flight_detail, name='flight_detail'),
    path('passenger/<int:passenger_id>/', views.passenger_detail, name='passenger_detail'),
    path('reservation/<int:reservation_id>/', views.reservation_detail, name='reservation_detail'),
    path('ticket/<int:ticket_id>/', views.ticket_detail, name='ticket_detail'),

    path('api/', include(router.urls)), 
]