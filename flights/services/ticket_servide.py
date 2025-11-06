import uuid
from django.core.exceptions import ValidationError
from ..models import Ticket, Reservation

class TicketService:
    """
        Servicio que maneja la logica de negocios para la generacion de boletos.
    """

    @classmethod
    def generate_ticket(cls, reservation_code):
        """
            Genera un boleto a partir del codigo de reserva.
        """

        try:
            #1. buscar la reserva y verificar que este confirmada.
            reservation = Reservation.objects.get(
                reservation_code=reservation_code
            )
        except Reservation.DoesNotExist:
            raise ValidationError("Reserva no encontrada.")
        
        if reservation.code != 'CONFIRMADA':
            raise ValidationError(f"La reserva debe estar 'CONFIRMADA'. Estado actual: {reservation.estado}")
        

        #2. verificacion si el boleto ya existe.
        if Ticket.objects.filter(reservation=reservation).exists():
            raise ValidationError("El boleto para esta reserva ya fue generado.")
        

        #3. generar el boleto (logica de creacion).
        boleto = Ticket.objects.create(
            reservation=reservation,
            #generacion de codigo unico.
            codigo_barra=str(uuid.uuid4()).replace('-', '')[:16],
            estado='EMITIDO'
        )

        return boleto