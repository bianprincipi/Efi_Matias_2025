from django.db import models
from django.core.exceptions import ValidationError
import random
import string

#generador de codigos de reservas aleatorias
def generate_reservation_code():
    length = 6
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


#entidad avion
class Aircraft(models.Model):
    model_name = models.CharField(max_length=50, verbose_name="Modelo")
    registration_number = models.CharField(max_length=10, unique=True, verbose_name="Matrícula")
    capacity = models.PositiveIntegerField(verbose_name="Capacidad Total")

    def __str__(self):
        return f"{self.model_name} ({self.registration_number})"
    
    class Meta:
        verbose_name = "Avión"
        verbose_name_plural = "Aviones"
    

#entidad asiento
class Seat(models.Model):
    aircraft = models.ForeignKey(Aircraft, on_delete=models.CASCADE, related_name='seats', verbose_name="Avión")
    seat_number = models.CharField(max_length=5, verbose_name="Número de Asiento")
    is_window_seat = models.BooleanField(default=False, verbose_name="Asiento de Ventanilla")

    CLASS_CHOICES = [
        ('ECONOMY', 'Económica'),
        ('BUSINESS', 'Negocios'),
        ('FIRST', 'Primera Clase'),
    ]
    seat_class = models.CharField(max_length=10, choices=CLASS_CHOICES, verbose_name="Clase de Asiento")

    def __str__(self):
        return f"{self.seat_number} - {self.aircraft.registration_number}"
    
    class Meta:
        verbose_name = "Asiento"
        verbose_name_plural = "Asientos"
        unique_together = ('aircraft', 'seat_number')


#entidad vuelo
class Flight(models.Model):
    aircraft = models.ForeignKey(Aircraft, on_delete=models.PROTECT, related_name='flights', verbose_name="Avión Asignado")
    flight_number = models.CharField(max_length=10, unique=True, verbose_name="Número de Vuelo")
    origin = models.CharField(max_length=100, verbose_name="Origen")
    destination = models.CharField(max_length=100, verbose_name="Destino")
    departure_time = models.DateTimeField(verbose_name="Hora de Salida")
    arrival_time = models.DateTimeField(verbose_name="Hora de Llegada")

    def clean(self):
        # Validación: Hora de llegada posterior a la de salida
        if self.departure_time and self.arrival_time and self.arrival_time <= self.departure_time:
            raise ValidationError("La hora de llegada debe ser posterior a la hora de salida.")
        
        if self.aircraft and self.aircraft.capacity <= 0:
             raise ValidationError("El avión asignado no tiene una capacidad de asientos válida (capacidad = 0).")

    def __str__(self):
        return f"Vuelo {self.flight_number}: {self.origin} -> {self.destination}"
    
    class Meta:
        verbose_name = "Vuelo"
        verbose_name_plural = "Vuelos"
        ordering = ['departure_time']


#entidad pasajero
class Passenger(models.Model):
    first_name = models.CharField(max_length=30, verbose_name="Nombre")
    last_name = models.CharField(max_length=30, verbose_name="Apellido")
    email = models.EmailField(unique=True, verbose_name="Correo Electrónico")
    phone_number = models.CharField(max_length=15, blank=True, null=True, verbose_name="Número de Teléfono")

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    
    class Meta:
        verbose_name = "Pasajero"
        verbose_name_plural = "Pasajeros"


#entidad reserva
class Reservation(models.Model):
    passenger = models.ForeignKey(Passenger, on_delete=models.CASCADE, related_name='reservations', verbose_name="Pasajero")
    flight = models.ForeignKey(Flight, on_delete=models.CASCADE, related_name='reservations', verbose_name="Vuelo")
    seat = models.ForeignKey(Seat, on_delete=models.PROTECT, related_name='reservations', verbose_name="Asiento")
    reservation_code = models.CharField(max_length=6, unique=True, default=generate_reservation_code, verbose_name="Código de Reserva")
    booking_date = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Reserva")

    def clean(self):
        # Validación 1: El asiento debe pertenecer al avión del vuelo.
        if self.seat and self.flight and self.seat.aircraft != self.flight.aircraft:
            raise ValidationError({
                'seat': f"El asiento {self.seat.seat_number} pertenece al avión {self.seat.aircraft.registration_number}, "
                f"pero el vuelo {self.flight.flight_number} usa el avión {self.flight.aircraft.registration_number}."
            })
    
    def save(self, *args, **kwargs):
        self.full_clean() 
        # Validación 2: No exceder la capacidad del avión
        current_reservations_count = Reservation.objects.filter(flight=self.flight).exclude(pk=self.pk).count()
        
        total_reservas_final = current_reservations_count + 1
        capacidad = self.flight.aircraft.capacity
        
        if total_reservas_final > capacidad:
            raise ValidationError(f"Capacidad excedida. El vuelo {self.flight.flight_number} solo tiene {capacidad} asientos.")
            
        super().save(*args, **kwargs) # Llama al método save original
        
    def __str__(self):
        return f"Reserva {self.reservation_code} para Vuelo {self.flight.flight_number} - {self.passenger.last_name}"
    
    class Meta:
        verbose_name = "Reserva"
        verbose_name_plural = "Reservas"
        unique_together = ('flight', 'seat')


#entidad boleto
class Ticket(models.Model):
    reservation = models.OneToOneField(Reservation, on_delete=models.CASCADE, primary_key='ticket', verbose_name="Reserva")
    booking_reference = models.CharField(max_length=10, unique=True, default=generate_reservation_code, editable=False, verbose_name="Referencia de Billete")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Precio")
    issue_date = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Emisión")
    is_checked_in = models.BooleanField(default=False, verbose_name="Check-in Realizado")

    def __str__(self):
        return f"Billete {self.booking_reference} - ({self.reservation.passenger.last_name})"
    
    class Meta:
        verbose_name = "Billete"
        verbose_name_plural = "Billetes"