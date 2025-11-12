from django.db import models
from django.core.exceptions import ValidationError
from django import forms

import random
import string
import uuid

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

    base_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00,
        verbose_name="Precio Base"
    )

    def clean(self):
        # 🚨 NUEVA VALIDACIÓN DE CAPACIDAD 🚨
        if self.aircraft:
            # 1. Contar cuántos asientos ya tiene registrado ESTE avión (excluyendo el asiento actual si es una edición)
            existing_seats_count = Seat.objects.filter(aircraft=self.aircraft).exclude(pk=self.pk).count()
            
            # 2. Sumarle el asiento que estamos intentando guardar (+1)
            total_seats_if_saved = existing_seats_count + 1
            
            # 3. Comparar con la capacidad del avión
            aircraft_capacity = self.aircraft.capacity

            if total_seats_if_saved > aircraft_capacity:
                raise ValidationError({
                    'aircraft': f"Este avión (Matrícula: {self.aircraft.registration_number}) tiene una capacidad máxima de {aircraft_capacity} asientos. Ya tiene {existing_seats_count} registrados y no puede agregar más."
                })
        
        # Validar unicidad del número de asiento dentro del avión (si no lo tienes ya)
        if self.aircraft and Seat.objects.filter(aircraft=self.aircraft, seat_number=self.seat_number).exclude(pk=self.pk).exists():
             raise ValidationError({
                'seat_number': f"El asiento {self.seat_number} ya está registrado para el avión {self.aircraft.registration_number}."
            })

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
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

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


class Passenger(models.Model):
    first_name = models.CharField(max_length=30, verbose_name="Nombre")
    last_name = models.CharField(max_length=30, verbose_name="Apellido")
    email = models.EmailField(unique=True, verbose_name="Correo Electrónico")
    phone_number = models.CharField(max_length=15, blank=True, null=True, verbose_name="Número de Teléfono")

    identification_number = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        verbose_name="DNI / Pasaporte"
    )
    
    birth_date = models.DateField(
        blank=True, 
        null=True, 
        verbose_name="Fecha de Nacimiento"
    )

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
    status = models.CharField(max_length=20, default='PENDING')
    is_confirmed = models.BooleanField(default=False)

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
    reservation = models.OneToOneField(
        'Reservation', 
        on_delete=models.CASCADE, 
        related_name='ticket',
        verbose_name='Reserva Asociada'
    )
    ticket_code = models.CharField(
        max_length=50, 
        unique=True,
        verbose_name='Código de Boleto'
    )
    issue_date = models.DateTimeField(auto_now_add=True)

    price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0.00,
        verbose_name='Precio del Boleto'
    )
    is_checked_in = models.BooleanField(
        default=False,
        verbose_name='Check-in Realizado'
    )
    
    def __str__(self):
        return self.ticket_code
    
    def save(self, *args, **kwargs):
        if not self.pk and not self.ticket_code:
            self.ticket_code = str(uuid.uuid4())
        
        super().save(*args, **kwargs)
    
class FlightManagementForm(forms.ModelForm):
    # Sobrescribimos el campo para usar un widget de fecha y hora más amigable
    departure_time = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        label="Hora de Salida"
    )
    arrival_time = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        label="Hora de Llegada Estimada"
    )

    class Meta:
        model = Flight
        fields = [
            'aircraft', 
            'flight_number', 
            'origin',         # Ahora son CharFields simples
            'destination',    # Ahora son CharFields simples
            'departure_time', 
            'arrival_time', 
            'price'           # Usaste 'price' en el modelo, no 'base_price'
        ]
        labels = {
            'aircraft': 'Avión',
            'flight_number': 'Número de Vuelo',
            'origin': 'Ciudad de Origen',
            'destination': 'Ciudad de Destino',
            'price': 'Precio Base del Vuelo' # Ajustado a 'price'
        }
        
    def clean(self):
        cleaned_data = super().clean()
        departure = cleaned_data.get('departure_time')
        arrival = cleaned_data.get('arrival_time')
        origin = cleaned_data.get('origin')
        destination = cleaned_data.get('destination')
        
        # Validación 1: Hora de Salida debe ser antes de Hora de Llegada
        if departure and arrival and departure >= arrival:
            self.add_error('arrival_time', 'La hora de llegada debe ser posterior a la hora de salida.')

        # Validación 2: Origen y Destino no deben ser iguales
        # Esta validación es importante para CharFields.
        if origin and destination and origin.lower() == destination.lower():
            self.add_error('destination', 'El origen y el destino no pueden ser la misma ciudad.')
            
        return cleaned_data