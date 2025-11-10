from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q
from django.contrib import messages
from django.core.exceptions import ValidationError
from .forms import FlightSearchForm, ReservationForm
from rest_framework import viewsets, filters, mixins
from .permissions import IsAirlineAdmin     
from rest_framework.permissions import IsAdminUser, AllowAny
from rest_framework.decorators import action 
from rest_framework.response import Response 
from rest_framework import status 
from rest_framework.views import APIView 
from django_filters.rest_framework import DjangoFilterBackend  
from .models import Flight, Passenger, Reservation, Seat, Ticket, Aircraft 
from .serializers import (
    VueloSerializer, 
    PassengerSerializer, 
    ReservationSerializer, 
    AircraftSerializer,
    SeatSerializer,
    TicketSerializer,
    UserProfileSerializer  
) 
import uuid #generar codigo de barras
from .services.ticket_servide import TicketService
from django.contrib.admin.views.decorators import staff_member_required
import random
from .permissions import IsAirlineAdmin
from rest_framework.permissions import IsAdminUser, AllowAny, IsAuthenticated
from django.shortcuts import render
from django.contrib.auth import get_user_model

User = get_user_model()

# =======================================================================================
# 1. VISTAS TRADICIONALES DE DJANGO (Retornan HTML para el Front-end)
# =======================================================================================

def index(request):
    """
        Controlador principal. Muestra la página de búsqueda y los vuelos iniciales.
    """
    search_form = FlightSearchForm()

    try: 
        flights = Flight.objects.all().order_by('departure_time')[:5]
    except Exception:
        flights = []
    
    context = {
        'flights': flights,
        'search_form' : search_form,
        'page_title': "Bienvenido | Vuelos Disponibles"
    }
    return render(request, 'flights/index.html', context)


# ⚠️ NOTA: Esta vista tradicional (search_flights) puede ser eliminada si solo usas la API.
def search_flights(request):
    """
        Procesa el formulario de búsqueda de vuelos y muestra los resultados (retorna HTML).
    """
    results = Flight.objects.none() # Inicializa un QuerySet vacío
    
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
    """
    Muestra los detalles de un vuelo específico y maneja la creación de una reserva (POST).
    """
    flight = get_object_or_404(Flight, pk=flight_id)
    aircraft = flight.aircraft

    reserved_seat_ids = Reservation.objects.filter(flight=flight).values_list('seat_id', flat=True)
    all_seats = Seat.objects.filter(aircraft=aircraft).order_by('row_number', 'letter')

    if request.method == 'POST':
        form = ReservationForm(request.POST, flight=flight)
        
        if form.is_valid():
            code = ''.join(random.choices('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=6))

            reservation = form.save(commit=False)
            reservation.flight = flight
            reservation.reservation_code = code
            
            reservation.save()
            
            return redirect('index') # Redirigir a una página de confirmación
        
    else:
        form = ReservationForm(flight=flight)
        form.fields['seat'].queryset = all_seats.exclude(id__in=reserved_seat_ids)

    seats_by_row = {}
    for seat in all_seats:
        is_reserved = seat.id in reserved_seat_ids
        seats_by_row.setdefault(seat.row_number, []).append({
            'object': seat,
            'is_reserved': is_reserved
        })
        
    context = {
        'flight': flight,
        'aircraft': aircraft,
        'form': form,
        'seats_by_row': seats_by_row,
        'page_title': f"Reservar Vuelo {flight.flight_number}",
    }
    return render(request, 'flights/flight_detail.html', context)


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

@staff_member_required #solo permite si el usuario ha iniciado sesion y es staff/admin
def admin_dashboard(request):
    """
        Muestra el panel de control del administrador.
    """
    context = {
        'page_title': 'Panel de Administración.'
    }
    return render(request, 'flights/admin_dashboard.html', context)


@staff_member_required
def manage_flights(request):
    """
    Lista todos los vuelos del sistema.
    """
    all_flights = Flight.objects.all().order_by('-departure_time')
    context = {
        'page_title': 'Gestión de Vuelos',
        'flights': all_flights,
        # 'create_url': '/flights/dashboard/vuelos/crear/'  # Ejemplo para futuros botones
    }
    return render(request, 'flights/manage_flights.html', context) # Debes crear manage_flights.html

@staff_member_required
def manage_reservations(request):
    """
    Lista todas las reservas del sistema con detalles precargados.
    """
    all_reservations = Reservation.objects.all().select_related(
        'flight', 
        'passenger', 
        'seat'
    ).order_by('-booking_date')

    context = {
        'page_title': 'Gestión de Reservas',
        'reservations': all_reservations,
    }
    return render(request, 'flights/manage_reservations.html', context) # Debes crear manage_reservations.html

@staff_member_required
def manage_aircrafts(request):
    """
    Lista todos los aviones/aeronaves del sistema.
    """
    all_aircrafts = Aircraft.objects.all().order_by('model_name')
    context = {
        'page_title': 'Gestión de Aviones',
        'aircrafts': all_aircrafts,
    }
    return render(request, 'flights/manage_aircrafts.html', context) # Debes crear manage_aircrafts.html

@staff_member_required
def manage_passengers(request):
    """
    Lista todos los perfiles de pasajeros (diferentes del User normal si tienes un modelo Passenger).
    """
    all_passengers = Passenger.objects.all().order_by('last_name')
    context = {
        'page_title': 'Gestión de Pasajeros',
        'passengers': all_passengers,
    }
    return render(request, 'flights/manage_passengers.html', context) # Debes crear manage_passengers.html

@staff_member_required
def manage_users(request):
    """
    Lista todos los usuarios (incluyendo clientes y staff).
    """
    all_users = User.objects.all().order_by('date_joined')
    context = {
        'page_title': 'Gestión de Cuentas de Usuario',
        'users': all_users,
    }
    return render(request, 'flights/manage_users.html', context) # Debes crear manage_users.html

# =======================================================================================
# 2. VISTAS DE DJANGO REST FRAMEWORK (Retornan JSON para la API)
# =======================================================================================

class SearchFlightsAPIView(APIView):
    """
    Endpoint dedicado para la búsqueda de vuelos por origen, destino y fecha.
    Es completamente público (para el cliente/pasajero).
    Endpoint: /api/vuelos/buscar/
    """
    permission_classes = [AllowAny] 

    def get(self, request, format=None):
        origin = request.query_params.get('origin')
        destination = request.query_params.get('destination')
        date = request.query_params.get('date') 
        
        queryset = Flight.objects.all()
        
        if origin:
            queryset = queryset.filter(origin=origin)
        if destination:
            queryset = queryset.filter(destination=destination)
        if date:
            # Filtra por la parte de la fecha del campo datetime (ej: '2025-12-31')
            queryset = queryset.filter(departure_time__date=date) 
            
        results = queryset.order_by('departure_time')
        
        serializer = VueloSerializer(results, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class VueloViewSet(viewsets.ModelViewSet):
    """
    ViewSet para la Gestión de Vuelos. Implementa CRUD, filtrado y permisos de Admin.
    Endpoints: /api/vuelos/
    """
    queryset = Flight.objects.all()
    serializer_class = VueloSerializer
    
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['origin', 'destination', 'departure_time']
    
    def get_permissions(self):
        # Permite list, retrieve y 'pasajeros' (información de búsqueda) a cualquiera.
        if self.action in ['list', 'retrieve', 'pasajeros']:
            permission_classes = [AllowAny] 
        else:
            # Requiere Admin para: create, update, partial_update, destroy
            permission_classes = [IsAirlineAdmin] 
        
        return [permission() for permission in permission_classes]
    
    @action(detail=True, methods=['get'], url_path='pasajeros', permission_classes=[AllowAny])
    def pasajeros(self, request, pk=None):
        """Devuelve todos los pasajeros que tienen una reserva confirmada para este vuelo."""
        flight = self.get_object() 

        reservations = Reservation.objects.filter(
            flight=flight,
            estado__in=['CONFIRMADA', 'EMITIDO']
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
    # Requiere que el usuario esté logueado (tenga un token JWT válido)
    permission_classes = [IsAuthenticated] 

    def get(self, request):
        # request.user es el usuario autenticado gracias al token JWT
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)

class PassengerViewSet(viewsets.ModelViewSet):
    """
    ViewSet para la Gestión de Pasajeros. 
    Permite: Registrar (POST), Detalle (GET /<id>), y Listar Reservas asociadas.
    Endpoints: /api/pasajeros/
    """
    queryset = Passenger.objects.all()
    serializer_class = PassengerSerializer
    
    def get_permissions(self):
        # Permite: create (registro), retrieve (ver detalle), reservas_activas a cualquiera.
        if self.action in ['create', 'retrieve', 'reservas', 'reservas_activas']:
            permission_classes = [AllowAny] 
        else: 
            # Requiere Admin para: list, update, partial_update, destroy
            permission_classes = [IsAirlineAdmin]
        
        return [permission() for permission in permission_classes]

    @action(detail=True, methods=['get'], url_path='reservas_activas', permission_classes=[AllowAny])
    def reservas_activas(self, request, pk=None):
        """Devuelve solo las reservas activas (confirmadas o pendientes) de un pasajero."""
        passenger = self.get_object() 
        
        active_states = ['PENDIENTE', 'CONFIRMADA', 'EMITIDO'] 
        
        active_reservations = Reservation.objects.filter(
            passenger=passenger, 
            estado__in=active_states 
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
    Endpoints: /api/reservas/
    """
    queryset = Reservation.objects.all()
    serializer_class = ReservationSerializer
    
    def get_permissions(self):
        # Permite crear la reserva a cualquiera (cliente)
        if self.action == 'create':
            permission_classes = [AllowAny]
        # Permite ver el detalle a cualquiera
        elif self.action == 'retrieve':
             permission_classes = [AllowAny]
        else:
            # Requiere Admin para el resto (list, update, destroy si los incluyeras)
            permission_classes = [IsAirlineAdmin] 
        return [permission() for permission in permission_classes]
    
    def perform_create(self, serializer):
        # Asigna el usuario que está autenticado a través del token JWT
        # Nota: Asume que tu modelo Reservation tiene un campo 'user' o 'passenger' que es un ForeignKey.
        # Si tienes un campo 'user' (Foreign Key al modelo User):
        serializer.save(user=self.request.user) 
        
        # Si tienes un campo 'passenger' (Foreign Key a tu modelo Passenger) y quieres obtener el objeto Passenger
        # asociado al User logueado (si tienes un modelo Passenger asociado 1 a 1 con User):
        # try:
        #     passenger_instance = Passenger.objects.get(user=self.request.user)
        #     serializer.save(passenger=passenger_instance)
        # except Passenger.DoesNotExist:
        #     raise Exception("No se encontró un perfil de Pasajero asociado al usuario logueado.")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(
                {"message": f"Reserva creada con éxito. Código: {serializer.instance.reservation_code}",
                 "data": serializer.data}, 
                status=status.HTTP_201_CREATED, 
                headers=headers
            )
        except ValidationError as e:
            return Response({"error": e.message_dict}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['patch'], url_path='estado', permission_classes=[IsAirlineAdmin])
    def cambiar_estado(self, request, pk=None):
        """Permite cambiar el estado de la reserva. (Solo Admin)."""
        
        reservation = self.get_object()
        new_state = request.data.get('estado')

        if not new_state:
            return Response({"error": "Debe proporcionar el nuevo estado de la reserva ('estado')."}, 
                            status=status.HTTP_400_BAD_REQUEST)
        
        # ⚠️ Aquí deberías agregar la lógica real para validar y cambiar el estado en el modelo
        try:
            # reservation.estado = new_state # Descomentar y validar si es un estado válido
            # reservation.save()
            print(f"Estado de reserva {reservation.reservation_code} cambiado a {new_state}.")
            
            return Response(
                {"message": f"Estado de la reserva {reservation.reservation_code} actualizado a {new_state}.",
                 "codigo_reserva": reservation.reservation_code},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response({"error": "El estado proporcionado no es válido o ocurrió un error interno al guardar."},
                            status=status.HTTP_400_BAD_REQUEST)


class AircraftViewSet(viewsets.ModelViewSet):
    """
    ViewSet para la Gestión de Aviones.
    Endpoints: /api/aviones/
    """
    queryset = Aircraft.objects.all()
    serializer_class = AircraftSerializer
    
    def get_permissions(self):
        # Permite crear la reserva SOLO si está autenticado (con token JWT)
        if self.action == 'create':
            permission_classes = [IsAuthenticated]
        # Permite ver el detalle a cualquiera
        elif self.action == 'retrieve':
             permission_classes = [AllowAny]
        else:
            # Requiere Admin para el resto (list, update, destroy si los incluyeras)
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
            return Response({"error": "Debe proporcionar el ID del vuelo ('vuelo_id') como parámetro de consulta."}, 
                            status=status.HTTP_400_BAD_REQUEST)
        
        try:
            flight = Flight.objects.get(pk=flight_id, aircraft=aircraft)
        except Flight.DoesNotExist:
            return Response({"error": "Vuelo no encontrado o no asignado a este avión."}, 
                            status=status.HTTP_404_NOT_FOUND)

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
    Endpoints: /api/boletos/
    """
    queryset = Ticket.objects.all().select_related('reservation__flight', 'reservation__passenger', 'reservation__seat')
    serializer_class = TicketSerializer
    lookup_field = 'codigo_barra' 
    
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
            return Response({"error": "Debe proporcionar el código de reserva ('reservation_code')."}, 
                        status=status.HTTP_400_BAD_REQUEST)
            
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
            return Response({"error": f"Error interno al generar el boleto: {str(e)}"}, 
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)