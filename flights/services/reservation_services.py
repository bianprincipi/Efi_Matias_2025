from django.core.exceptions import ValidationError
from django.db import transaction
from ..models import Reservation, Flight, Seat, Passenger


class ReservationService:
    """
        Servicio que maneja la logica de negocio para la creacion y validacion de reservas
    """

    @classmethod
    def create_reservation(cls, flight_id, seat_id, passenger_data):
        """
            Crea una reserva, asegurando la atomicidad y la validacion de disponibilidad.

            Recibe:
                - flight_id: id del vuelo.
                - seat_id: id del asiento.
                - passenger_data: datos del pasajero o id si el mismo ya existe.
        """

        try:
            flight = Flight.objects.get(id=flight_id)
            seat = Seat.objects.get(id=seat_id)
        except (Flight.DoesNotExist, Seat.DoesNotExist):
            raise ValidationError("Vuelo o Asiento no encontrado.")
        
        #1. validacion de vuelo/asiento: asegura que el asiento pertenece al avion del vuelo.
        if seat.aircraft != flight.aircraft:
            raise ValidationError("El asiento no pertenece al avion asignado a este vuelo.")
        

        #2. validacion de disponibilidad (aseguramos que el asiento no este ya reservado en este vuelo).
        if Reservation.objects.filter(flight=flight, seat=seat).exists():
            raise ValidationError("El asiento ya se encuentra reservado para este vuelo.")
        

        #3. obtener o crear pasajero.
        try:
            passenger = Passenger.objects.get(id=passenger_data.get('id'))
        except Passenger.DoesNotExist:
            #logica alternativa: crear pasajero
            raise ValidationError("Pasajero no encontrado. Registrelo en la seccion 'Registrar Pasajero'.")
        

        #4. creacion de la reserva.
        with transaction.atomic():
            reservation = Reservation.objects.create(
                flight=flight,
                seat=seat,
                passenger=passenger,
                estado = 'PENDIENTE' #estado inicial.
            )
            return reservation

