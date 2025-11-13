from rest_framework import serializers
from ..models import Aircraft, Seat, Flight, Reservation, Passenger, Ticket 
from django.contrib.auth import get_user_model

User = get_user_model()

class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer para el registro de nuevos usuarios.
    """
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    password2 = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'}, label="Confirmar Contraseña")

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password', 'password2']

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError("Las contraseñas no coinciden.")
        return data

    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        return user

class AircraftSerializer(serializers.ModelSerializer):
    class Meta:
        model = Aircraft
        fields = ['id', 'registration_number', 'model_name', 'capacity'] 

class SeatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Seat
        fields = ['id', 'seat_number', 'seat_class', 'base_price']

# Serializer para la creación y actualización de Reservas
class ReservationSerializer(serializers.ModelSerializer):
    # Campos solo de lectura para mostrar info en el listado
    flight_number = serializers.CharField(source='flight.flight_number', read_only=True)
    passenger_name = serializers.CharField(source='passenger.first_name', read_only=True)
    
    class Meta:
        model = Reservation
        # El usuario enviará flight_id, passenger_id y seat_id (PKs)
        fields = ['id', 'flight', 'passenger', 'seat', 
                  'booking_date', 'is_confirmed', 'reservation_code', 
                  'flight_number', 'passenger_name']
        read_only_fields = ['reservation_code', 'booking_date', 'is_confirmed']

# Serializer simple para cambiar el estado de confirmación/cancelación
class ReservationStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reservation
        fields = ['is_confirmed']

class TicketSerializer(serializers.ModelSerializer):
    """
    Serializa la información del boleto, incluyendo el detalle de la reserva.
    """
    # Muestra todos los detalles de la reserva asociada
    reservation_details = ReservationSerializer(source='reservation', read_only=True)
    
    # Campos derivados para acceso rápido
    flight_number = serializers.CharField(source='reservation.flight.flight_number', read_only=True)
    seat_number = serializers.CharField(source='reservation.seat.seat_number', read_only=True)

    class Meta:
        model = Ticket
        fields = ['id', 'ticket_code', 'issue_date', 'reservation', 
                  'flight_number', 'seat_number', 'reservation_details']
        read_only_fields = ['ticket_code', 'issue_date']

class PassengerReportSerializer(serializers.ModelSerializer):
    """ Serializer simplificado para reportes de pasajeros. """
    class Meta:
        model = Passenger
        fields = ['id', 'first_name', 'last_name', 'document_number']

class FlightSerializer(serializers.ModelSerializer):
    """ Serializer para mostrar información básica del Vuelo. """

    class Meta:
        model = Flight
        # Incluye los campos clave para el reporte
        fields = ['id', 'flight_number', 'departure_time', 'arrival_time', 'origin', 'destination']

class ActiveReservationSerializer(serializers.ModelSerializer):
    """ Serializer para listar reservas activas. """
    flight_details = FlightSerializer(source='flight', read_only=True)
    seat_number = serializers.CharField(source='seat.seat_number', read_only=True)
    
    class Meta:
        model = Reservation
        fields = [
            'reservation_code', 'is_confirmed', 'booking_date', 
            'flight_details', 'seat_number'
        ]