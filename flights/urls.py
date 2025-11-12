from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views 
from .views import (FlightListView, FlightCreateView, FlightDeleteView, FlightUpdateView, FlightSeatManagementView)

# Crea el router para las vistas de la API (REST Framework)
router = DefaultRouter()
router.register(r'vuelos', views.VueloViewSet, basename='vuelo')         
router.register(r'pasajeros', views.PassengerViewSet, basename='pasajero') 
router.register(r'reservas', views.ReservationViewSet, basename='reserva') 
router.register(r'aviones', views.AircraftViewSet, basename='avion')     
router.register(r'boletos', views.TicketViewSet, basename='boleto')     

app_name = 'flights' 

urlpatterns = [
    
    # HOME PAGE 
    path('', views.index, name='index'),
    
    # BÚSQUEDA WEB 
    path('search/', views.search_flights, name='search_flights'),
    
    # DASHBOARD DE ADMINISTRADOR WEB
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),

    # GESTIÓN DE VUELOS (CRUD)
    path('dashboard/vuelos/', views.manage_flights, name='manage_flights'),
    path('dashboard/vuelos/<int:pk>/asientos/', 
         FlightSeatManagementView.as_view(), 
         name='flight_seat_management'),
    path('dashboard/vuelos/crear/', views.create_flight, name='create_flight'),
    path('dashboard/vuelos/editar/<int:flight_id>/', views.edit_flight, name='edit_flight'),
    path('dashboard/vuelos/eliminar/<int:flight_id>/', views.delete_flight, name='delete_flight'),

    # --- GESTIÓN DE VUELOS (CRUD) ---
    path('dashboard/vuelos/', FlightListView.as_view(), name='flight_list'),
    path('dashboard/vuelos/crear/', FlightCreateView.as_view(), name='flight_create'),
    path('dashboard/vuelos/<int:pk>/editar/', FlightUpdateView.as_view(), name='flight_update'),
    path('dashboard/vuelos/<int:pk>/eliminar/', FlightDeleteView.as_view(), name='flight_delete'),

    # Rutas CRUD de Reservas
    path('dashboard/reservas/', views.manage_reservations, name='manage_reservations'),
    path('dashboard/reservas/crear/', views.create_reservation, name='create_reservation'),
    path('dashboard/reservas/editar/<int:reservation_id>/', views.edit_reservation, name='edit_reservation'),
    path('dashboard/reservas/eliminar/<int:reservation_id>/', views.delete_reservation, name='delete_reservation'),
    
    # Rutas CRUD de Boletos (Tickets)
    path('dashboard/boletos/', views.manage_tickets, name='manage_tickets'),
    path('dashboard/boletos/crear/', views.create_ticket, name='create_ticket'),
    path('dashboard/boletos/editar/<int:ticket_id>/', views.edit_ticket, name='edit_ticket'),
    path('dashboard/boletos/eliminar/<int:ticket_id>/', views.delete_ticket, name='delete_ticket'),

    # Rutas CRUD de Aviones (Aircraft)
    path('dashboard/aviones/', views.manage_aircrafts, name='manage_aircrafts'),
    path('dashboard/aviones/crear/', views.create_aircraft, name='create_aircraft'),
    path('dashboard/aviones/editar/<int:aircraft_id>/', views.edit_aircraft, name='edit_aircraft'),
    path('dashboard/aviones/eliminar/<int:aircraft_id>/', views.delete_aircraft, name='delete_aircraft'),

    # GESTIÓN DE AVIONES (CRUD CBVs)
    path('dashboard/aviones/', views.AircraftListView.as_view(), name='manage_aircraft'),
    path('dashboard/aviones/crear/', views.AircraftCreateView.as_view(), name='create_aircraft'),
    path('dashboard/aviones/editar/<int:pk>/', views.AircraftUpdateView.as_view(), name='edit_aircraft'),
    path('dashboard/aviones/eliminar/<int:pk>/', views.AircraftDeleteView.as_view(), name='delete_aircraft'),

    # Rutas CRUD de Asientos (Seat)
    path('dashboard/asientos/', views.manage_seats, name='manage_seats'),
    path('dashboard/asientos/crear/', views.create_seat, name='create_seat'),
    path('dashboard/asientos/editar/<int:seat_id>/', views.edit_seat, name='edit_seat'),
    path('dashboard/asientos/eliminar/<int:seat_id>/', views.delete_seat, name='delete_seat'),
    
    # GESTIÓN DE OTROS MODELOS
    path('dashboard/reservas/', views.manage_reservations, name='manage_reservations'),
    path('dashboard/aviones/', views.manage_aircrafts, name='manage_aircrafts'),
    path('dashboard/pasajeros/', views.manage_passengers, name='manage_passengers'),
    path('dashboard/usuarios/', views.manage_users, name='manage_users'),
    
    # RUTAS DE DETALLE WEB 
    path('<int:flight_id>/', views.flight_detail, name='flight_detail'), 
    path('passenger/<int:passenger_id>/', views.passenger_detail, name='passenger_detail'),
    path('reservation/<int:reservation_id>/', views.reservation_detail, name='reservation_detail'),
    path('ticket/<int:ticket_id>/', views.ticket_detail, name='ticket_detail'),

    # GESTIÓN DE USUARIOS 
    path('dashboard/cuentas/', views.UserListView.as_view(), name='manage_users'),
    path('dashboard/cuentas/crear/', views.UserCreateView.as_view(), name='create_user'),
    path('dashboard/cuentas/editar/<int:pk>/', views.UserUpdateView.as_view(), name='edit_user'),
    path('dashboard/cuentas/eliminar/<int:pk>/', views.UserDeleteView.as_view(), name='delete_user'),

    # GESTIÓN DE PASAJEROS (CRUD CBVs) - Mantenemos solo un set
    path('dashboard/pasajeros/', views.PassengerListView.as_view(), name='manage_passengers'),
    path('dashboard/pasajeros/crear/', views.PassengerCreateView.as_view(), name='create_passenger'),
    path('dashboard/pasajeros/editar/<int:pk>/', views.PassengerUpdateView.as_view(), name='edit_passenger'),
    path('dashboard/pasajeros/eliminar/<int:pk>/', views.PassengerDeleteView.as_view(), name='delete_passenger'),
    path('pasajero/<int:passenger_id>/', views.passenger_detail, name='passenger_detail'),

    # Rutas para la Gestión de Pasajeros
    path('management/passengers/', views.PassengerListView.as_view(), name='passenger_list'),
    path('management/passengers/new/', views.PassengerCreateView.as_view(), name='passenger_create'),
    path('management/passengers/<int:pk>/edit/', views.PassengerUpdateView.as_view(), name='passenger_update'),
    path('management/passengers/<int:pk>/delete/', views.PassengerDeleteView.as_view(), name='passenger_delete'),

    # RUTAS API REST
    path('api/v1/', include('flights.api.urls')),

    # ENDPOINT DE PERFIL
    path('api/profile/', views.UserProfileAPIView.as_view(), name='api_profile'),
    
    # ENDPOINT DE BÚSQUEDA API DEDICADO
    path('api/vuelos/buscar/', views.SearchFlightsAPIView.as_view(), name='flight-search-api'),
    
    # ENDPOINTS CRUD (Generados por el Router)
    path('api/', include(router.urls)), 
]