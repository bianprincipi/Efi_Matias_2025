from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views 

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
    path('dashboard/vuelos/crear/', views.create_flight, name='create_flight'),
    path('dashboard/vuelos/editar/<int:flight_id>/', views.edit_flight, name='edit_flight'),
    path('dashboard/vuelos/eliminar/<int:flight_id>/', views.delete_flight, name='delete_flight'),

    # GESTIÓN DE RESERVAS (CRUD) <--- ¡NUEVAS!
    path('dashboard/reservas/', views.manage_reservations, name='manage_reservations'),
    path('dashboard/reservas/crear/', views.create_reservation, name='create_reservation'),
    path('dashboard/reservas/editar/<int:reservation_id>/', views.edit_reservation, name='edit_reservation'),
    path('dashboard/reservas/eliminar/<int:reservation_id>/', views.delete_reservation, name='delete_reservation'),
    
    # GESTIÓN DE BOLETOS/TICKETS (CRUD) <--- ¡NUEVAS!
    path('dashboard/boletos/', views.manage_tickets, name='manage_tickets'),
    path('dashboard/boletos/crear/', views.create_ticket, name='create_ticket'),
    path('dashboard/boletos/editar/<int:ticket_id>/', views.edit_ticket, name='edit_ticket'),
    path('dashboard/boletos/eliminar/<int:ticket_id>/', views.delete_ticket, name='delete_ticket'),
    
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

    # RUTAS API REST
    
    # ENDPOINT DE PERFIL
    path('api/profile/', views.UserProfileAPIView.as_view(), name='api_profile'),
    
    # ENDPOINT DE BÚSQUEDA API DEDICADO
    path('api/vuelos/buscar/', views.SearchFlightsAPIView.as_view(), name='flight-search-api'),
    
    # ENDPOINTS CRUD (Generados por el Router)
    path('api/', include(router.urls)), 
]