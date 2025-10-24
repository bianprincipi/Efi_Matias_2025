from django.shortcuts import render, get_object_or_404
from django.db.models import Q #busquedas complejas
from .models import Flight, Aircraft, Seat, Passenger, Reservation, Ticket

def index(request):
    """Vista principal que muestra una lista de vuelos disponibles."""
    flights = Flight.objects.all().order_by('departure_time')
    context = {
        'flights': flights,
        'page_title': 'Lista de Vuelos Disponibles'
    }
    return render(request, 'flights/index.html', context)


def flight_detail(request, flight_id):
    """Vista que muestra los detalles de un vuelo específico."""
    flight = get_object_or_404(Flight, id=flight_id)
    seats = Seat.objects.filter(aircraft=flight.aircraft).order_by('seat_number')
    context = {
        'flight': flight,
        'seats': seats,
        'page_title': f'Detalles del Vuelo {flight.flight_number}'
    }
    return render(request, 'flights/flight_detail.html', context)


def search_flights(request):
    """Vista para buscar vuelos por origen, destino o número de vuelo."""
    query = request.GET.get('q', '')
    results = []
    if query:
        results = Flight.objects.filter(
            Q(origin__icontains=query) |
            Q(destination__icontains=query) |
            Q(flight_number__icontains=query)
        ).order_by('departure_time')
    context = {
        'query': query,
        'results': results,
        'page_title': 'Resultados de Búsqueda de Vuelos'
    }
    return render(request, 'flights/search_results.html', context)


def passenger_detail(request, passenger_id):
    """Vista que muestra los detalles de un pasajero específico."""
    passenger = get_object_or_404(Passenger, id=passenger_id)
    reservations = Reservation.objects.filter(passenger=passenger).select_related('flight', 'seat')
    context = {
        'passenger': passenger,
        'reservations': reservations,
        'page_title': f'Detalles del Pasajero {passenger.first_name} {passenger.last_name}'
    }
    return render(request, 'flights/passenger_detail.html', context)


def reservation_detail(request, reservation_id):
    """Vista que muestra los detalles de una reserva específica."""
    reservation = get_object_or_404(Reservation, id=reservation_id)
    context = {
        'reservation': reservation,
        'page_title': f'Detalles de la Reserva {reservation.reservation_code}'
    }
    return render(request, 'flights/reservation_detail.html', context)


def ticket_detail(request, ticket_id):
    """Vista que muestra los detalles de un boleto específico."""
    ticket = get_object_or_404(Ticket, id=ticket_id)
    context = {
        'ticket': ticket,
        'page_title': f'Detalles del Boleto {ticket.booking_reference}'
    }
    return render(request, 'flights/ticket_detail.html', context)


