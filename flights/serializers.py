from rest_framework import serializers
from .models import (
    Aircraft, Flight, Passenger, Reservation, Seat, Ticket
)
from .services.reservation_services import ReservationService
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User


class AircraftDetailSerializer(serializers.ModelSerializer):
    """Serializador simple para mostrar información del Avión asignado."""
    class Meta:
        model = Aircraft
        fields = ['registration_number', 'model_name', 'capacity']


class SeatDetailSerializer(serializers.ModelSerializer):
    """Serializador para mostrar información del Asiento."""
    class Meta:
        model = Seat
        fields = ['id', 'seat_number', 'seat_class', 'is_window_seat']


class VueloSerializer(serializers.ModelSerializer):
    """Serializador para el modelo Flight."""
    aircraft = AircraftDetailSerializer(read_only=True)

    aircraft_id = serializers.PrimaryKeyRelatedField(
        queryset=Aircraft.objects.all(),
        source='aircraft',
        write_only=True,
        required=True
    )

    class Meta:
        model = Flight
        fields = [
            'id', 'flight_number', 'origin', 'destination',
            'departure_time', 'arrival_time', 'aircraft',
            'aircraft_id'
        ]
        read_only_fields = ['id', 'aircraft', 'flight_number']


class PassengerSerializer(serializers.ModelSerializer):
    """Serializador para el modelo Passenger (Registro y Detalle)."""
    email = serializers.EmailField(required=True)

    class Meta:
        model = Passenger
        fields = ['id', 'first_name', 'last_name', 'email', 'phone_number']
        read_only_fields = ['id']


class ReservationSerializer(serializers.ModelSerializer):
    """
    Serializador para el modelo Reservation.
    Se usa para la creación de nuevas reservas (POST).
    """
    passenger_name = serializers.CharField(source='passenger.first_name', read_only=True)
    flight_number = serializers.CharField(source='flight.flight_number', read_only=True)
    seat_number = serializers.CharField(source='seat.seat_number', read_only=True)

    passenger_id = serializers.PrimaryKeyRelatedField(
        queryset=Passenger.objects.all(), source='passenger', write_only=True
    )
    flight_id = serializers.PrimaryKeyRelatedField(
        queryset=Flight.objects.all(), source='flight', write_only=True
    )
    seat_id = serializers.PrimaryKeyRelatedField(
        queryset=Seat.objects.all(), source='seat', write_only=True
    )

    # CAMBIO: exponer 'status' del modelo (lo dejamos solo lectura; se cambia vía acciones del ViewSet)
    status = serializers.CharField(read_only=True)  # CAMBIO

    class Meta:
        model = Reservation
        fields = [
            'id', 'reservation_code', 'booking_date',
            'passenger_id', 'flight_id', 'seat_id',
            'passenger_name', 'flight_number', 'seat_number',
            'status',  # CAMBIO
        ]
        read_only_fields = [
            'id', 'reservation_code', 'booking_date',
            'passenger_name', 'flight_number', 'seat_number',
            'status',  # CAMBIO
        ]

    def create(self, validated_data):
        flight_id = validated_data['flight'].id
        seat_id = validated_data['seat'].id
        passenger_data = validated_data['passenger']

        try:
            reservation = ReservationService.create_reservation(
                flight_id=flight_id,
                seat_id=seat_id,
                passenger_data=passenger_data
            )
            return reservation
        except ValidationError as e:
            raise serializers.ValidationError({"error": e.message})

    def validate(self, data):
        flight = data.get('flight')
        seat = data.get('seat')

        if seat.aircraft != flight.aircraft:
            raise serializers.ValidationError(
                {"seat_id": "El asiento seleccionado no pertenece al avión asignado a este vuelo."}
            )

        if Reservation.objects.filter(flight=flight, seat=seat).exists():
            raise serializers.ValidationError(
                {"seat_id": "Este asiento ya se encuentra reservado para el vuelo seleccionado."}
            )

        return data


class SeatSerializer(serializers.ModelSerializer):
    """Serializador para el modelo Seat."""
    class Meta:
        model = Seat
        fields = ['id', 'aircraft', 'seat_number', 'is_window_seat', 'seat_class']
        read_only_fields = ['id', 'aircraft']


class AircraftSerializer(serializers.ModelSerializer):
    """Serializador para el modelo Aircraft (Avión)."""
    class Meta:
        model = Aircraft
        fields = ['id', 'model_name', 'registration_number', 'capacity']
        read_only_fields = ['id']


class TicketSerializer(serializers.ModelSerializer):
    """
    Serializador para el modelo Ticket.
    Se usa para la creación y visualización de boletos.
    """
    # CAMBIO: mapear "ticket_number" al campo real del modelo ("booking_reference")
    ticket_number = serializers.CharField(source='booking_reference', read_only=True)  # CAMBIO

    reservation_code = serializers.CharField(source='reservation.reservation_code', read_only=True)
    passenger_name = serializers.CharField(source='reservation.passenger.first_name', read_only=True)
    flight_number = serializers.CharField(source='reservation.flight.flight_number', read_only=True)
    seat_number = serializers.CharField(source='reservation.seat.seat_number', read_only=True)

    reservation_id = serializers.PrimaryKeyRelatedField(
        queryset=Reservation.objects.all(), source='reservation', write_only=True
    )

    class Meta:
        model = Ticket
        fields = [
            'id',
            'ticket_number',   # CAMBIO: alias de booking_reference
            'issue_date',
            'reservation_id',
            'reservation_code',
            'passenger_name',
            'flight_number',
            'seat_number'
        ]
        # CAMBIO: antes era read_only_fields = fields (bug). Ahora explicitamos:
        read_only_fields = [
            'id',
            'ticket_number',
            'issue_date',
            'reservation_code',
            'passenger_name',
            'flight_number',
            'seat_number'
        ]  # CAMBIO


# =========================================================
# Perfil de Usuario (Login Diferenciado)
# =========================================================
class UserProfileSerializer(serializers.ModelSerializer):
    """
    Devuelve la información del usuario autenticado,
    incluyendo el estado crucial de 'is_staff'.
    """
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'is_staff')
        read_only_fields = ('username', 'email', 'is_staff')
