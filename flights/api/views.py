# flights/api/views.py (Crea este archivo)

from rest_framework import generics, status, serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.shortcuts import get_object_or_404
from ..models import Aircraft, Flight, Reservation, Seat, Ticket, Passenger
from .serializers import AircraftSerializer, SeatSerializer, ReservationSerializer, ReservationStatusSerializer, TicketSerializer, PassengerReportSerializer, ActiveReservationSerializer
from django.db import transaction
from rest_framework.response import Response
import uuid
from rest_framework.renderers import JSONRenderer
from rest_framework.decorators import api_view, permission_classes

# Endpoint 1: Listar Aviones
class AircraftListAPIView(generics.ListAPIView):
    queryset = Aircraft.objects.all()
    serializer_class = AircraftSerializer
    permission_classes = [AllowAny]

# Endpoint 2: Obtener Layout/Asientos de un Avión
class AircraftSeatsAPIView(APIView):
    def get(self, request, pk):
        aircraft = get_object_or_404(Aircraft, pk=pk)
        
        # Obtenemos todos los asientos asociados a ese avión
        seats = aircraft.seat_set.all().order_by('seat_number')
        
        serializer = SeatSerializer(seats, many=True)
        return Response(serializer.data)
    
# Endpoint 3: Verificar Disponibilidad de un Asiento en un Vuelo
class SeatAvailabilityAPIView(APIView):
    """
    Verifica si un asiento específico está disponible para un vuelo dado.
    Requiere flight_id y seat_id en el cuerpo (POST) o como parámetros de consulta (GET).
    """
    def get(self, request, *args, **kwargs):
        flight_id = request.query_params.get('flight_id')
        seat_id = request.query_params.get('seat_id')

        if not flight_id or not seat_id:
            return Response({"error": "Se requieren 'flight_id' y 'seat_id'."}, status=400)

        # 1. Verificar si el vuelo existe
        flight = get_object_or_404(Flight, pk=flight_id)
        
        # 2. Verificar si el asiento existe y pertenece al avión del vuelo
        seat = get_object_or_404(Seat, pk=seat_id, aircraft=flight.aircraft)

        # 3. Verificar si existe una reserva para ese vuelo Y ese asiento
        is_reserved = Reservation.objects.filter(
            flight=flight,
            seat=seat
        ).exists()

        if is_reserved:
            return Response({
                "available": False,
                "message": f"El asiento {seat.seat_number} ya está reservado para este vuelo."
            })
        else:
            return Response({
                "available": True,
                "message": f"El asiento {seat.seat_number} está disponible."
            })

class ReservationCreateAPIView(generics.CreateAPIView):
    """
    Endpoint para crear una reserva y seleccionar un asiento.
    Realiza validación de disponibilidad de asiento.
    """
    queryset = Reservation.objects.all()
    serializer_class = ReservationSerializer
    permission_classes = [IsAuthenticated] # Requiere que el usuario esté logueado

    @transaction.atomic
    def perform_create(self, serializer):
        flight_id = self.request.data.get('flight')
        seat_id = self.request.data.get('seat')
        
        # 1. Validación de Disponibilidad: Buscar si el asiento ya está reservado en ese vuelo
        is_reserved = Reservation.objects.filter(
            flight_id=flight_id, 
            seat_id=seat_id,
            is_confirmed=True # Solo reservadas confirmadas bloquean
        ).exists()

        if is_reserved:
            raise serializers.ValidationError(
                {"seat": "Este asiento ya no está disponible para este vuelo."}
            )

        # 2. Generar código único y guardar
        # Esta lógica DEBE estar en el modelo o en una función de servicio para ser robusta
        # Aquí la simplificamos para el ejemplo.
        reservation_code = f"RES-{uuid.uuid4().hex[:6].upper()}"
        
        # Asignar el pasajero logueado (asumiendo que User se relaciona con Passenger)
        # Por simplicidad, asumiremos que el frontend enviará passenger_id
        
        return serializer.save(reservation_code=reservation_code, is_confirmed=True)

class ReservationStatusUpdateAPIView(generics.UpdateAPIView):
    """
    Endpoint para confirmar o cancelar una reserva cambiando el estado is_confirmed.
    Requiere el PK de la reserva.
    """
    queryset = Reservation.objects.all()
    serializer_class = ReservationStatusSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['patch']

class FlightAvailabilityDetailAPIView(APIView):
    """
    Retorna la lista de todos los asientos del avión de un vuelo, 
    marcando su estado de disponibilidad (reservado/disponible).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, flight_pk):
        flight = get_object_or_404(Flight, pk=flight_pk)
        aircraft = flight.aircraft

        # Obtener todos los asientos del avión
        all_seats = aircraft.seat_set.all().order_by('seat_number')

        # Obtener los IDs de los asientos YA reservados y confirmados para este vuelo
        reserved_seat_ids = Reservation.objects.filter(
            flight=flight,
            is_confirmed=True
        ).values_list('seat_id', flat=True)

        seat_layout = []
        for seat in all_seats:
            seat_layout.append({
                "id": seat.id,
                "seat_number": seat.seat_number,
                "seat_class": seat.seat_class,
                "base_price": seat.base_price,
                "is_available": seat.id not in reserved_seat_ids
            })

        return Response({
            "flight_number": flight.flight_number,
            "aircraft": aircraft.registration_number,
            "total_capacity": aircraft.capacity,
            "seats": seat_layout
        })

class TicketGenerateAPIView(APIView):
    """
    Genera un boleto (Ticket) a partir de una reserva confirmada.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        # 1. Buscar la Reserva
        reservation = get_object_or_404(Reservation, pk=pk)

        # 2. Validar el estado
        if not reservation.is_confirmed:
            return Response(
                {"error": "La reserva no está confirmada y no se puede emitir el boleto."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 3. Validar si el boleto ya existe
        if Ticket.objects.filter(reservation=reservation).exists():
            return Response(
                {"error": "El boleto para esta reserva ya ha sido generado."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 4. Generar el código único y crear el Ticket
        # Lógica de generación de código (ejemplo: TKT-RESCODE-01)
        ticket_code = f"TKT-{reservation.reservation_code[:8]}-{uuid.uuid4().hex[:4].upper()}"
        
        ticket = Ticket.objects.create(
            reservation=reservation,
            ticket_code=ticket_code
            # issue_date se establece automáticamente
        )
        
        serializer = TicketSerializer(ticket)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class TicketDetailByCodeAPIView(APIView):
    """
    Consulta la información detallada de un boleto usando su código único.
    """
    permission_classes = [IsAuthenticated] # O AllowAny, dependiendo si quieres que sea público

    def get(self, request, ticket_code):
        try:
            # Búsqueda por el campo ticket_code
            ticket = Ticket.objects.get(ticket_code=ticket_code)
        except Ticket.DoesNotExist:
            return Response(
                {"error": "Boleto no encontrado o código incorrecto."},
                status=status.HTTP_404_NOT_FOUND
            )
            
        serializer = TicketSerializer(ticket)
        return Response(serializer.data)
    
class PassengersByFlightReportAPIView(APIView):
    """
    Reporte: Obtiene todos los pasajeros con reservas confirmadas para un vuelo específico.
    """
    permission_classes = [IsAuthenticated] # Solo personal autorizado

    def get(self, request, flight_pk):
        flight = get_object_or_404(Flight, pk=flight_pk)

        # Buscar las reservas confirmadas para el vuelo
        confirmed_reservations = Reservation.objects.filter(
            flight=flight,
            is_confirmed=True
        ).select_related('passenger') # Optimiza la carga del objeto Passenger

        # Extraer los objetos Passenger únicos de esas reservas
        passengers = [res.passenger for res in confirmed_reservations]
        
        # Serializar los datos del pasajero
        serializer = PassengerReportSerializer(passengers, many=True)

        return Response({
            "flight_number": flight.flight_number,
            # 🚨 LÍNEAS PROBLEMÁTICAS 🚨
            "origin": flight.origin,  # Ejemplo si el campo es 'name'
            "destination": flight.destination, # Ejemplo si el campo es 'name'
            "total_passengers": len(passengers),
            "passengers": serializer.data
        })

class ActiveReservationsByPassengerAPIView(APIView):
    """
    Reporte: Obtiene todas las reservas activas (confirmadas) para un pasajero.
    """
    permission_classes = [IsAuthenticated] # Solo personal autorizado

    def get(self, request, passenger_pk):
        passenger = get_object_or_404(Passenger, pk=passenger_pk)

        # Buscar reservas que estén confirmadas
        active_reservations = Reservation.objects.filter(
            passenger=passenger,
            is_confirmed=True
        ).select_related('flight', 'seat') # Optimiza la carga de relaciones

        # Serializar las reservas activas
        serializer = ActiveReservationSerializer(active_reservations, many=True)
        
        return Response({
            "passenger": f"{passenger.first_name} {passenger.last_name}",
            "document": passenger.identification_number,
            "active_reservations_count": len(active_reservations),
            "reservations": serializer.data
        })