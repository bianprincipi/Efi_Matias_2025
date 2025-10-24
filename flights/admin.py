from django.contrib import admin
from .models import Aircraft, Flight, Passenger, Seat, Reservation, Ticket

#administracion de aviones
@admin.register(Aircraft)
class AircraftAdmin(admin.ModelAdmin):
    list_display = ('registration_number', 'model', 'capacity')
    search_fields = ('registration_number', 'model')


#administracion de asientos
@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    list_display = ('seat_number', 'get_aircraft_reg', 'seat_class', 'is_window_seat')
    list_filter = ('seat_class', 'is_window_seat', 'aircraft')
    search_fields = ('seat_number', 'aircraft__registration_number')
    raw_id_fields = ('aircraft',)

    #funcion para mostrar la matricula del avion
    def get_aircraft_reg(self, obj):
        return obj.aircraft.registration_number
    get_aircraft_reg.short_description = 'Matrícula del Avión'


#administracion de vuelos
class FlightAdmin(admin.ModelAdmin):
    list_display = ('flight_number', 'origin', 'destination', 'departure_time', 'aircraft')
    list_filter = ('origin', 'destination', 'departure_time')
    search_fields = ('flight_number', 'origin', 'destination')
    raw_id_fields = ('aircraft',)


#administracion de pasajeros
@admin.register(Passenger)
class PassengerAdmin(admin.ModelAdmin):
    list_display = ('last_name', 'first_name', 'email', 'phone_number')
    search_fields = ('last_name', 'first_name', 'email')

#administracion de reservas
@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('reservation_code', 'flight', 'passenger', 'seat', 'booking_date')
    list_filter = ('flight', 'booking_date')
    search_fields = ('reservation_code', 'passenger__last_name', 'flight__flight_number')
    raw_id_fields = ('passenger', 'flight', 'seat')


#administracion de tickets
@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('booking_reference', 'reservation_id', 'price', 'is_checked_in', 'issue_date')
    list_filter = ('is_checked_in', 'issue_date')
    search_fields = ('booking_reference', 'reservation__reservation_code')