# 1. Librerías Estándar de Python
import random
import uuid
from datetime import datetime

# 2. Librerías de Terceros (Django, DRF, etc.)
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from rest_framework import viewsets, filters, mixins, status
from rest_framework.permissions import IsAdminUser, AllowAny, IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.utils.dateparse import parse_date  # NUEVO

# 3. Librerías Locales (de tu propio proyecto)
# Importaciones de Formularios
from .forms import FlightSearchForm, ReservationForm, FlightForm
# Importaciones de Modelos
from .models import Flight, Passenger, Reservation, Seat, Ticket, Aircraft
# Importaciones de Serializadores y Permisos
from .serializers import (
    VueloSerializer, PassengerSerializer, ReservationSerializer,
    AircraftSerializer, SeatSerializer, TicketSerializer, UserProfileSerializer
)
from .permissions import IsAirlineAdmin
# Importaciones de Servicios
from .services.ticket_servide import TicketService  # (mantengo el nombre tal como lo tenés)

User = get_user_model()

# =======================================================================================
# 1. VISTAS TRADICIONALES DE DJANGO (Retornan HTML para el Front-end)
# =======================================================================================

def index(request):
    search_form = FlightSearchForm()
    try:
        flights = Flight.objects.all().order_by('departure_time')[:5]
    except Exception:
        flights = []
    context = {
        'flights': flights,
        'search_form': search_form,
        'page_title': "Bienvenido | Vuelos Disponibles"
    }
    return render(request, 'flights/index.html', context)


def my_reservations(request):
    # Solo renderiza la plantilla; el JS hace la llamada a la API
    return render(request, 'flights/my_reservations.html', {
        'page_title': 'Mis reservas'
    })


def search_flights(request):
    results = Flight.objects.none()
    form = FlightSearchForm(request.GET)
    if form.is_valid():
        origin = form.cleaned_data.get('origin')
        destination = form.cleaned_data.get('destination')
        date = form.cleaned_data.get('date')
        queryset = Flight.objects.all()
        if origin:
            queryset = queryset.filter(origin=origin)
        if destination:
            queryset = queryset.filter(destination=destination)
        if date:
            queryset = queryset.filter(departure_time__date=date)
        results = queryset.order_by('departure_time')
    context = {
        'search_form': form,
        'results': results,
        'page_title': "Resultados de Búsqueda"
    }
    return render(request, 'flights/search_results.html', context)


def flight_detail(request, flight_id):
    flight = get_object_or_404(Flight, pk=flight_id)
    aircraft = flight.aircraft
    reserved_seat_ids = Reservation.objects.filter(flight=flight).values_list('seat_id', flat=True)

    # Orden correcto por seat_number
    all_seats = Seat.objects.filter(aircraft=aircraft).order_by('seat_number')

    if request.method == 'POST':
        form = ReservationForm(request.POST, flight=flight)
        if form.is_valid():
            code = ''.join(random.choices('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=6))
            reservation = form.save(commit=False)
            reservation.flight = flight
            reservation.reservation_code = code
            reservation.save()
            return redirect('flights:index')  # FIX: namespace
    else:
        form = ReservationForm(flight=flight)
        form.fields['seat'].queryset = all_seats.exclude(id__in=reserved_seat_ids)

    # Agrupar por "fila" deducida de seat_number (ej: '12A' -> '12')
    def seat_row_from_number(seat_number: str) -> str:
        return ''.join(ch for ch in seat_number if ch.isdigit()) or seat_number

    seats_by_row = {}
    for seat in all_seats:
        is_reserved = seat.id in reserved_seat_ids
        row_key = seat_row_from_number(seat.seat_number)
        seats_by_row.setdefault(row_key, []).append({
            'object': seat,
            'is_reserved': is_reserved
        })

    context = {
        'flight': flight,
        'aircraft': aircraft,
        'form': form,
        'seats_by_row': seats_by_row,
        'page_title': f" Reservar Vuelo {flight.flight_number}",
    }
    return render(request, 'flights/flight_detail.html', context)


def passenger_detail(request, passenger_id):
    passenger = get_object_or_404(Passenger, id=passenger_id)
    reservations = Reservation.objects.filter(passenger=passenger).select_related('flight', 'seat')
    context = {
        'passenger': passenger,
        'reservations': reservations,
        'page_title': f'Detalles del Pasajero {passenger.first_name} {passenger.last_name}'
    }
    return render(request, 'flights/passenger_detail.html', context)


def reservation_detail(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id)
    context = {
        'reservation': reservation,
        'page_title': f'Detalles de la Reserva {reservation.reservation_code}'
    }
    return render(request, 'flights/reservation_detail.html', context)


def ticket_detail(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    context = {
        'ticket': ticket,
        'page_title': f'Detalles del Boleto {ticket.booking_reference}'
    }
    return render(request, 'flights/ticket_detail.html', context)


@staff_member_required
def admin_dashboard(request):
    context = {
        'page_title': 'Panel de Administración.'
    }
    return render(request, 'flights/admin_dashboard.html', context)


# VISTAS DE GESTIÓN (LISTADO)
@staff_member_required
def manage_flights(request):
    all_flights = Flight.objects.all().order_by('-departure_time')
    context = {
        'page_title': 'Gestión de Vuelos',
        'flights': all_flights,
    }
    return render(request, 'flights/manage_flights.html', context)


@staff_member_required
def manage_reservations(request):
    all_reservations = Reservation.objects.all().select_related(
        'flight',
        'passenger',
        'seat'
    ).order_by('-booking_date')
    context = {
        'page_title': 'Gestión de Reservas',
        'reservations': all_reservations,
    }
    return render(request, 'flights/manage_reservations.html', context)


@staff_member_required
def manage_aircrafts(request):
    all_aircrafts = Aircraft.objects.all().order_by('model_name')
    context = {
        'page_title': 'Gestión de Aviones',
        'aircrafts': all_aircrafts,
    }
    return render(request, 'flights/manage_aircrafts.html', context)


@staff_member_required
def manage_passengers(request):
    all_passengers = Passenger.objects.all().order_by('last_name')
    context = {
        'page_title': 'Gestión de Pasajeros',
        'passengers': all_passengers,
    }
    return render(request, 'flights/manage_passengers.html', context)


@staff_member_required
def manage_users(request):
    all_users = User.objects.all().order_by('date_joined')
    context = {
        'page_title': 'Gestión de Cuentas de Usuario',
        'users': all_users,
    }
    return render(request, 'flights/manage_users.html', context)


# =========================================================
# VISTAS CRUD PARA VUELOS
# =========================================================

@staff_member_required
def create_flight(request):
    if request.method == 'POST':
        form = FlightForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Vuelo creado con éxito.")
            return redirect('flights:manage_flights')
    else:
        form = FlightForm()

    context = {
        'page_title': 'Crear Nuevo Vuelo',
        'form': form,
    }
    return render(request, 'flights/flight_form.html', context)


@staff_member_required
def edit_flight(request, flight_id):
    flight = get_object_or_404(Flight, pk=flight_id)
    if request.method == 'POST':
        form = FlightForm(request.POST, instance=flight)
        if form.is_valid():
            form.save()
            messages.success(request, f"Vuelo #{flight.flight_number} actualizado con éxito.")
            return redirect('flights:manage_flights')
    else:
        form = FlightForm(instance=flight)

    context = {
        'page_title': f'Editar Vuelo #{flight.flight_number}',
        'form': form,
    }
    return render(request, 'flights/flight_form.html', context)


@staff_member_required
def delete_flight(request, flight_id):
    flight = get_object_or_404(Flight, pk=flight_id)
    if request.method == 'POST':
        flight_number = flight.flight_number
        flight.delete()
        messages.warning(request, f"Vuelo #{flight_number} eliminado correctamente.")
        return redirect('flights:manage_flights')
    return redirect('flights:manage_flights')


# =======================================================================================
# 2. VISTAS DE DJANGO REST FRAMEWORK (Retornan JSON para la API)
# =======================================================================================

class SearchFlightsAPIView(APIView):
    """
    Endpoint dedicado para la búsqueda de vuelos por origen, destino y fecha.
    Es completamente público (para el cliente/pasajero).
    Endpoint: /flights/api/vuelos/buscar/
    """
    permission_classes = [AllowAny]

    def get(self, request, format=None):
        origin = (request.query_params.get('origin') or '').strip()
        destination = (request.query_params.get('destination') or '').strip()
        date_str = (request.query_params.get('date') or '').strip()

        qs = Flight.objects.all()

        # Búsqueda flexible: exacto o parcial (case-insensitive)
        if origin:
            qs = qs.filter(Q(origin__iexact=origin) | Q(origin__icontains=origin))
        if destination:
            qs = qs.filter(Q(destination__iexact=destination) | Q(destination__icontains=destination))

        # Fecha opcional: YYYY-MM-DD o DD/MM/YYYY
        if date_str:
            d = parse_date(date_str)
            if d is None:
                try:
                    d = datetime.strptime(date_str, "%d/%m/%Y").date()
                except ValueError:
                    d = None
            if d:
                qs = qs.filter(departure_time__date=d)

        results = qs.order_by('departure_time')
        serializer = VueloSerializer(results, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class VueloViewSet(viewsets.ModelViewSet):
    """
    ViewSet para la Gestión de Vuelos. Implementa CRUD, filtrado y permisos de Admin.
    Endpoints: /flights/api/vuelos/
    """
    queryset = Flight.objects.all()
    serializer_class = VueloSerializer

    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['origin', 'destination', 'departure_time']

    def get_permissions(self):
        # Permite list, retrieve y 'pasajeros' a cualquiera.
        if self.action in ['list', 'retrieve', 'pasajeros']:
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAirlineAdmin]
        return [permission() for permission in permission_classes]

    @action(detail=True, methods=['get'], url_path='pasajeros', permission_classes=[AllowAny])
    def pasajeros(self, request, pk=None):
        """Devuelve todos los pasajeros que tienen una reserva confirmada para este vuelo."""
        flight = self.get_object()

        reservations = Reservation.objects.filter(
            flight=flight,
            status__in=['confirmed']  # estados nuevos
        ).select_related('passenger')

        passengers = [res.passenger for res in reservations]
        serializer = PassengerSerializer(passengers, many=True)
        return Response({
            "vuelo": flight.flight_number,
            "total_pasajeros_activos": len(passengers),
            "pasajeros": serializer.data
        })


# =========================================================
# Nueva Vista API para obtener el Perfil del Usuario
# =========================================================
class UserProfileAPIView(APIView):
    """
    Vista protegida (requiere token JWT) que devuelve el perfil del
    usuario autenticado, incluyendo su estado de is_staff.
    Endpoint: /flights/api/profile/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)


class PassengerViewSet(viewsets.ModelViewSet):
    """
    ViewSet para la Gestión de Pasajeros.
    Permite: Registrar (POST), Detalle (GET /<id>), y Listar Reservas asociadas.
    Endpoints: /flights/api/pasajeros/
    """
    queryset = Passenger.objects.all()
    serializer_class = PassengerSerializer

    def get_permissions(self):
        if self.action in ['create', 'retrieve', 'reservas', 'reservas_activas']:
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAirlineAdmin]
        return [permission() for permission in permission_classes]

    @action(detail=True, methods=['get'], url_path='reservas_activas', permission_classes=[AllowAny])
    def reservas_activas(self, request, pk=None):
        """Devuelve solo las reservas activas (pendientes o confirmadas) de un pasajero."""
        passenger = self.get_object()

        active_status = ['pending', 'confirmed']

        active_reservations = Reservation.objects.filter(
            passenger=passenger,
            status__in=active_status
        ).select_related('flight', 'seat').order_by('booking_date')

        serializer = ReservationSerializer(active_reservations, many=True)
        return Response({
            "pasajero": f"{passenger.first_name} {passenger.last_name}",
            "reservas_activas_count": active_reservations.count(),
            "reservas": serializer.data
        })


class ReservationViewSet(viewsets.GenericViewSet,
                         mixins.CreateModelMixin,
                         mixins.RetrieveModelMixin):
    """
    ViewSet para la Gestión de Reservas.
    Permite: Crear (POST) para el Cliente, Detalle (GET) y Admin para el resto.
    Endpoints: /flights/api/reservas/
    """
    queryset = Reservation.objects.all().select_related('flight', 'passenger', 'seat')
    serializer_class = ReservationSerializer

    def get_permissions(self):
        # create/retrieve públicas; confirm/cancel administradas por decorator de acción
        if self.action in ['create', 'retrieve']:
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAirlineAdmin]
        return [permission() for permission in permission_classes]

    # perform_create no es necesario; el serializer usa ReservationService

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            instance = serializer.save()  # delega en serializer.create (ReservationService)
            headers = self.get_success_headers(serializer.data)
            return Response(
                {"message": f"Reserva creada con éxito. Código: {instance.reservation_code}",
                 "data": self.get_serializer(instance).data},
                status=status.HTTP_201_CREATED,
                headers=headers
            )
        except ValidationError as e:
            return Response({"error": getattr(e, 'message_dict', str(e))}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Compat: map de 'estado' (es) a 'status' (en)
    ESTADO_MAP = {
        'pendiente': 'pending',
        'confirmada': 'confirmed',
        'cancelada': 'canceled',
    }

    def get_queryset(self):
        qs = super().get_queryset()
        estado = self.request.query_params.get('estado')
        status_q = self.request.query_params.get('status')

        if estado and not status_q:
            mapped = self.ESTADO_MAP.get(estado.lower().strip())
            if mapped:
                qs = qs.filter(status=mapped)
        elif status_q:
            qs = qs.filter(status=status_q)
        return qs

    @action(detail=True, methods=['post'], permission_classes=[IsAirlineAdmin])
    def confirm(self, request, pk=None):
        """Confirma una reserva (Admin)."""
        reservation = self.get_object()
        if reservation.status == Reservation.STATUS_CONFIRMED:
            return Response({'detail': 'La reserva ya está confirmada.'}, status=status.HTTP_200_OK)
        reservation.confirm()
        return Response({'detail': 'Reserva confirmada.', 'status': reservation.status}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[IsAirlineAdmin])
    def cancel(self, request, pk=None):
        """Cancela una reserva (Admin)."""
        reservation = self.get_object()
        if reservation.status == Reservation.STATUS_CANCELED:
            return Response({'detail': 'La reserva ya está cancelada.'}, status=status.HTTP_200_OK)
        reservation.cancel()
        return Response({'detail': 'Reserva cancelada.', 'status': reservation.status}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['patch'], url_path='estado', permission_classes=[IsAirlineAdmin])
    def cambiar_estado(self, request, pk=None):
        """
        Compat: permite cambiar el estado con el parámetro 'estado' (es/en).
        Preferir usar /confirm y /cancel.
        """
        reservation = self.get_object()
        new_state = request.data.get('estado')
        if not new_state:
            return Response(
                {"error": "Debe proporcionar el nuevo estado de la reserva ('estado')."},
                status=status.HTTP_400_BAD_REQUEST
            )

        mapped = self.ESTADO_MAP.get(new_state.lower().strip(), new_state.lower().strip())
        if mapped not in ['pending', 'confirmed', 'canceled']:
            return Response({"error": "Estado no válido."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            if mapped == 'confirmed':
                reservation.confirm()
            elif mapped == 'canceled':
                reservation.cancel()
            else:
                reservation.status = Reservation.STATUS_PENDING
                reservation.save(update_fields=['status'])

            return Response(
                {"message": f"Estado de la reserva {reservation.reservation_code} actualizado a {reservation.status}.",
                 "codigo_reserva": reservation.reservation_code},
                status=status.HTTP_200_OK
            )
        except Exception:
            return Response(
                {"error": "No se pudo actualizar el estado."},
                status=status.HTTP_400_BAD_REQUEST
            )


class AircraftViewSet(viewsets.ModelViewSet):
    """
    ViewSet para la Gestión de Aviones.
    Endpoints: /flights/api/aviones/
    """
    queryset = Aircraft.objects.all()
    serializer_class = AircraftSerializer

    def get_permissions(self):
        if self.action == 'create':
            permission_classes = [IsAuthenticated]
        elif self.action == 'retrieve':
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAirlineAdmin]
        return [permission() for permission in permission_classes]

    @action(detail=True, methods=['get'], permission_classes=[AllowAny])
    def layout(self, request, pk=None):
        """Devuelve todos los asientos asociados al avión."""
        aircraft = self.get_object()
        seats = aircraft.seats.all().order_by('seat_number')
        serializer = SeatSerializer(seats, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], permission_classes=[AllowAny])
    def disponibilidad(self, request, pk=None):
        """
        Verifica y devuelve la lista de asientos disponibles para un vuelo
        específico en este avión.
        """
        aircraft = self.get_object()
        flight_id = request.query_params.get('vuelo_id')

        if not flight_id:
            return Response(
                {"error": "Debe proporcionar el ID del vuelo ('vuelo_id') como parámetro de consulta."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            flight = Flight.objects.get(pk=flight_id, aircraft=aircraft)
        except Flight.DoesNotExist:
            return Response(
                {"error": "Vuelo no encontrado o no asignado a este avión."},
                status=status.HTTP_404_NOT_FOUND
            )

        reserved_seat_ids = Reservation.objects.filter(flight=flight).values_list('seat__id', flat=True)

        available_seats = Seat.objects.filter(
            aircraft=aircraft
        ).exclude(
            id__in=reserved_seat_ids
        ).order_by('seat_number')

        serializer = SeatSerializer(available_seats, many=True)
        return Response({
            "vuelo_id": flight_id,
            "disponibles_count": available_seats.count(),
            "asientos": serializer.data
        })


class TicketViewSet(viewsets.GenericViewSet, mixins.RetrieveModelMixin):
    """
    ViewSet para la Gestión de Boletos. (Solo Admin).
    Endpoints: /flights/api/boletos/
    """
    queryset = Ticket.objects.all().select_related('reservation__flight', 'reservation__passenger', 'reservation__seat')
    serializer_class = TicketSerializer

    # Buscar por 'booking_reference' (existe en el modelo)
    lookup_field = 'booking_reference'

    def get_permissions(self):
        """Permisos: Requiere Admin para todas las acciones."""
        permission_classes = [IsAirlineAdmin]
        return [permission() for permission in permission_classes]

    @action(detail=False, methods=['post'], url_path='generar', permission_classes=[IsAirlineAdmin])
    def generar(self, request):
        """
        Genera un boleto a partir de una reserva confirmada (Solo Admin).
        """
        reservation_code = request.data.get('reservation_code')

        if not reservation_code:
            return Response(
                {"error": "Debe proporcionar el código de reserva ('reservation_code')."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            boleto = TicketService.generate_ticket(reservation_code)
            serializer = self.get_serializer(boleto)
            return Response({
                "message": "Boleto generado con éxito.",
                "data": serializer.data
            }, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response(
                {"error": f"Error interno al generar el boleto: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
