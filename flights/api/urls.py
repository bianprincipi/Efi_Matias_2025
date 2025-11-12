# flights/api/urls.py

from django.urls import path
from .views import (
    AircraftListAPIView, 
    AircraftSeatsAPIView, 
    SeatAvailabilityAPIView,
    ReservationCreateAPIView,
    ReservationStatusUpdateAPIView,
    FlightAvailabilityDetailAPIView,
    TicketGenerateAPIView,
    TicketDetailByCodeAPIView,
    PassengersByFlightReportAPIView,
    ActiveReservationsByPassengerAPIView,
)

urlpatterns = [
    # API: Listar todos los aviones
    path('aircrafts/', AircraftListAPIView.as_view(), name='api_aircraft_list'),
    
    # API: Obtener layout de asientos de un avión
    path('aircrafts/<int:pk>/seats/', AircraftSeatsAPIView.as_view(), name='api_aircraft_seats'),
    
    # API: Verificar disponibilidad de asiento
    path('availability/seat/', SeatAvailabilityAPIView.as_view(), name='api_seat_availability'),

    # API: Crear una reserva (POST)
    path('reservations/create/', ReservationCreateAPIView.as_view(), name='api_create_reservation'),
    
    # API: Cambiar estado de una reserva (PATCH)
    path('reservations/<int:pk>/status/', ReservationStatusUpdateAPIView.as_view(), name='api_update_reservation_status'),

    # API: Detalle de disponibilidad de asientos para un vuelo específico
    path('flights/<int:flight_pk>/seats/availability/', 
         FlightAvailabilityDetailAPIView.as_view(), 
         name='api_flight_availability_detail'),

    # API: Generar boleto (POST) - Usa la PK de la Reserva
    path('tickets/generate/<int:pk>/', TicketGenerateAPIView.as_view(), name='api_generate_ticket'),

    # API: Consultar boleto por código (GET)
    path('tickets/consult/<str:ticket_code>/', TicketDetailByCodeAPIView.as_view(), name='api_consult_ticket'),

    # 1. Pasajeros por Vuelo (GET)
    path('reports/flight/<int:flight_pk>/passengers/', 
         PassengersByFlightReportAPIView.as_view(), 
         name='api_report_passengers_by_flight'),
    
    # 2. Reservas Activas por Pasajero (GET)
    path('reports/passenger/<int:passenger_pk>/active_reservations/', 
         ActiveReservationsByPassengerAPIView.as_view(), 
         name='api_report_active_reservations_by_passenger'),
]