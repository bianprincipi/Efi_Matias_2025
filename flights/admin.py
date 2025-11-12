from django.contrib import admin
from .models import Aircraft, Flight, Passenger, Seat, Reservation, Ticket

# --- INLINES ---
# 1. Muestra Asientos dentro de Avión
class SeatInline(admin.TabularInline):
    model = Seat
    extra = 1
    raw_id_fields = ('aircraft',) # Es redundante aquí, pero buena práctica si se usara en otro admin

# 2. Muestra Reservas dentro de Vuelo
class ReservationInline(admin.TabularInline):
    model = Reservation
    extra = 1
    raw_id_fields = ('passenger', 'seat', 'flight') # Incluimos 'flight' por si es necesario en el formulario


# --- ADMINISTRACIÓN DE AVIONES (Aircraft) ---
@admin.register(Aircraft)
class AircraftAdmin(admin.ModelAdmin):
    list_display = ('registration_number', 'model', 'capacity') # Nota: Cambié 'model' por 'model_name' para coincidir con tu modelo
    search_fields = ('registration_number', 'model_name')
    inlines = [SeatInline] # <-- AGREGADO: Muestra los asientos del avión

# --- ADMINISTRACIÓN DE ASIENTOS (Seat) ---
@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    list_display = ('seat_number', 'get_aircraft_reg', 'seat_class', 'is_window_seat')
    list_filter = ('seat_class', 'is_window_seat', 'aircraft')
    search_fields = ('seat_number', 'aircraft__registration_number')
    raw_id_fields = ('aircraft',)

    def get_aircraft_reg(self, obj):
        return obj.aircraft.registration_number
    get_aircraft_reg.short_description = 'Matrícula del Avión'


# --- ADMINISTRACIÓN DE VUELOS (Flight) ---
@admin.register(Flight)
class FlightAdmin(admin.ModelAdmin):
    list_display = ('flight_number', 'origin', 'destination', 'departure_time', 'aircraft')
    list_filter = ('origin', 'destination', 'departure_time')
    search_fields = ('flight_number', 'origin', 'destination')
    raw_id_fields = ('aircraft',)
    inlines = [ReservationInline] # <-- AGREGADO: Muestra las reservas asociadas al vuelo


# --- ADMINISTRACIÓN DE PASAJEROS (Passenger) ---
@admin.register(Passenger)
class PassengerAdmin(admin.ModelAdmin):
    list_display = ('apellido', 'nombre', 'email', 'telefono')
    search_fields = ('apellido', 'nombre', 'email')

# --- ADMINISTRACIÓN DE RESERVAS (Reservation) ---
@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('reservation_code', 'flight', 'passenger', 'seat', 'booking_date')
    list_filter = ('flight', 'booking_date')
    search_fields = ('reservation_code', 'passenger__last_name', 'flight__flight_number')
    raw_id_fields = ('passenger', 'flight', 'seat')


# --- ADMINISTRACIÓN DE BILLETES (Ticket) ---
@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = (
        'get_reservation_code',  # 🚨 Usamos el nuevo método 🚨
        'ticket_code',
        'is_checked_in',         # Asumiendo que agregaste este campo
        'issue_date',
        'reservation',           # Puedes mostrar el objeto Reservation completo
    )
    
    # 🚨 DEFINICIÓN DEL MÉTODO QUE ACCEDE AL CÓDIGO DE RESERVA 🚨
    def get_reservation_code(self, obj):
        # obj es una instancia de Ticket. 
        # Accedemos a la Reserva (ForeignKey) y luego a su código.
        return obj.reservation.reservation_code
    
    get_reservation_code.short_description = 'Cód. Reserva' # Título de la columna