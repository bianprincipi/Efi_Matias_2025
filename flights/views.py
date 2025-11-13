import random 
import uuid 
import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q, Exists, OuterRef
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.views import View
from rest_framework import viewsets, filters, mixins, status
from rest_framework.permissions import IsAdminUser, AllowAny, IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from .forms import (
    FlightSearchForm, ReservationForm, FlightForm, ReservationManagementForm, 
    TicketManagementForm, AircraftManagementForm, SeatManagementForm, 
    PassengerManagementForm, UserManagementForm, UserUpdateForm, FlightManagementForm, CustomerRegistrationForm
)
from .models import Flight, Passenger, Reservation, Seat, Ticket, Aircraft 
from .serializers import (
    VueloSerializer, PassengerSerializer, ReservationSerializer, AircraftSerializer, 
    SeatSerializer, TicketSerializer, UserProfileSerializer
)
from .permissions import IsAirlineAdmin     
from .services.ticket_servide import TicketService
from .mixins import AdminRequiredMixin

User = get_user_model()
logger = logging.getLogger(__name__)

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
        'search_form' : search_form,
        'page_title': "Bienvenido | Vuelos Disponibles"
    }
    return render(request, 'flights/index.html', context)

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
            
        # 🚨 CORRECCIÓN: SOLO se usa 'aircraft' (la ForeignKey) en select_related
        # Se eliminan 'origin' y 'destination'
        results = queryset.select_related('aircraft').order_by('departure_time')
        
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
    all_seats = Seat.objects.filter(aircraft=aircraft).order_by('row_number', 'letter')
    if request.method == 'POST':
        form = ReservationForm(request.POST, flight=flight)
        if form.is_valid():
            code = ''.join(random.choices('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=6))
            reservation = form.save(commit=False)
            reservation.flight = flight
            reservation.reservation_code = code
            reservation.save()
            return redirect('index') 
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
    """
        Muestra los detalles d un pasajero especifivo, incluyendo todas sus reservar y tickets asociados.
    """
    try:
        #1. obtiene el pasajero o retorna 404 si no existe
        passenger = get_object_or_404(Passenger, pk=passenger_id)

        #2. consulta las reservas del pasajero
        reservations = Reservation.objects.filter(
            passenger=passenger
        ).select_related('flight', 'seat').order_by('-booking_date')

        #3. consulta los tickets del pasajero
        tickets = Ticket.objects.filter(
            reservation__id=reservations
        ).select_related('reservation')

    except Exception as e:
        #captura errores como si la tabla no existiera temporalmente
        messages.error(request, f"Error al cargar los datos del pasajero: {e}")
        return redirect('flights:manage_passengers')
    
    context = {
        'page_title': f"Detalle del Pasajero: {passenger.first_name} {passenger.last_name}",
        'passenger': passenger,
        'reservation': reservations,
        'tickets': tickets  
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
# VISTAS CRUD PARA VUELOS (NUEVAS)
# =========================================================

@staff_member_required
def create_flight(request):
    """
    Maneja la creación de un nuevo vuelo.
    """
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
    # Renderiza la plantilla de formulario
    return render(request, 'flights/flight_form.html', context) 

@staff_member_required
def edit_flight(request, flight_id):
    """
    Maneja la edición de un vuelo existente.
    """
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
    """
    Maneja la eliminación de un vuelo (requiere POST para la seguridad).
    """
    flight = get_object_or_404(Flight, pk=flight_id)
    
    if request.method == 'POST': 
        flight_number = flight.flight_number
        flight.delete()
        messages.warning(request, f"Vuelo #{flight_number} eliminado correctamente.")
        return redirect('flights:manage_flights')
    
    # Si alguien intenta acceder por GET, simplemente redirigimos para evitar eliminaciones accidentales
    return redirect('flights:manage_flights')


@login_required
def manage_flights(request):
    """
        Muestra la lista de vuelos (para el panel admin).
    """
    if not request.user.is_staff:
        messages.error(request, "Acceso denegado. Solo personal autorizado.")
        return redirect('flights:index')
    
    flights = Flight.objects.all().order_by('departure_time')
    context = {
        'flights': flights,
        'page_title': 'Gestion de Vuelos'
    }
    return render(request, 'flights/manage_flights.html', context)

@login_required
def create_flight(request):
    """Permite al admin crear un nuevo vuelo."""
    
    if not request.user.is_staff:
        messages.error(request, "Acceso denegado.")
        return redirect('flights:index')
    
    # 1. Si es POST, procesamos los datos
    if request.method == 'POST':
        form = FlightForm(request.POST)
        if form.is_valid():
            # Caso 1: POST VÁLIDO (Redirige)
            form.save()
            messages.success(request, f"El vuelo #{form.cleaned_data['flight_number']} ha sido creado exitosamente.")
            return redirect('flights:manage_flights')
    
    # 2. Si es GET, o si es POST INVÁLIDO, inicializamos el formulario.
    else:
        # Caso 3: GET (Inicializa el formulario vacío)
        form = FlightForm()
        
    # 3. Renderizado final (GET o POST Inválido)
    context = {
        'form': form,
        'page_title': 'Crear Nuevo Vuelo'
    }
    return render(request, 'flights/flight_form.html', context)
    
@login_required
def edit_flight(request, flight_id):
    """Permite al administrador editar un vuelo existente."""
    
    if not request.user.is_staff:
        messages.error(request, "Acceso denegado.")
        return redirect('flights:index')
    
    flight = get_object_or_404(Flight, pk=flight_id)
    
    # 1. Si es POST, procesamos los datos
    if request.method == 'POST':
        form = FlightForm(request.POST, instance=flight)
        if form.is_valid():
            # Caso 1: POST VÁLIDO (Redirige)
            form.save()
            messages.success(request, f"El vuelo #{flight.flight_number} ha sido actualizado exitosamente!")
            return redirect('flights:manage_flights')
    
    # 2. Si es GET, o si es POST INVÁLIDO, inicializamos/mantenemos el formulario
    else:
        # Caso 3: GET (Inicializa el formulario con los datos existentes del vuelo)
        form = FlightForm(instance=flight)
        
    # 3. Renderizado final (GET o POST Inválido)
    context = {
        'form': form,
        'flight': flight,
        'page_title': f'Editar Vuelo #{flight.flight_number}'
    }
    return render(request, 'flights/flight_form.html', context)
    
@login_required
def delete_flight(request, flight_id):
    """Permite al administrador eliminar un vuelo, verificando si tiene reservas."""
    
    if not request.user.is_staff:
        messages.error(request, "Acceso denegado. Solo personal autorizado puede eliminar vuelos.")
        return redirect('flights:index')

    if request.method == 'POST':
        flight = get_object_or_404(Flight, pk=flight_id)
        flight_number = flight.flight_number
        
        reservation_count = Reservation.objects.filter(flight=flight).count()
        
        if reservation_count > 0:
            messages.error(
                request, 
                f"No se puede eliminar el vuelo #{flight_number}. Tiene {reservation_count} reserva(s) asociada(s)."
            )
        else:
            try:
                flight.delete()
                messages.success(request, f"El vuelo #{flight_number} ha sido eliminado exitosamente.")
            except Exception as e:
                messages.error(request, f"Error al eliminar el vuelo #{flight_number}: {e}")
            
    # Redirige siempre a la lista de gestión de vuelos
    return redirect('flights:manage_flights')

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
        serializer.save(user=self.request.user) 

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


class AircraftListView(AdminRequiredMixin, ListView):
    """Muestra la lista de todos los aviones."""
    model = Aircraft
    template_name = 'flights/aircraft/manage_aircraft.html'
    context_object_name = 'aircrafts'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Gestión de Aviones'
        return context

class AircraftCreateView(AdminRequiredMixin, CreateView):
    """Permite crear un nuevo registro de avión."""
    model = Aircraft
    form_class = AircraftManagementForm
    template_name = 'flights/aircraft/aircraft_form.html'
    success_url = reverse_lazy('flights:manage_aircraft')
    
    def form_valid(self, form):
        messages.success(self.request, "El avión fue creado exitosamente.")
        return super().form_valid(form)

class AircraftUpdateView(AdminRequiredMixin, UpdateView):
    """Permite editar un registro de avión existente."""
    model = Aircraft
    form_class = AircraftManagementForm
    template_name = 'flights/aircraft/aircraft_form.html'
    success_url = reverse_lazy('flights:manage_aircraft')
    
    def form_valid(self, form):
        messages.success(self.request, "El avión fue actualizado exitosamente.")
        return super().form_valid(form)

class AircraftDeleteView(AdminRequiredMixin, DeleteView):
    """Permite eliminar un registro de avión."""
    model = Aircraft
    template_name = 'flights/aircraft/aircraft_confirm_delete.html'
    context_object_name = 'aircraft'
    success_url = reverse_lazy('flights:manage_aircraft')
    
    def form_valid(self, form):
        messages.success(self.request, f"Avión '{self.object}' eliminado exitosamente.")
        return super().form_valid(form)

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
            # TicketService debe estar importado correctamente en views.py
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

# =========================================================
# VISTAS DE ADMINISTRACIÓN DE AVIONES (CRUD)
# =========================================================

@login_required
def manage_aircrafts(request):
    """Muestra la lista de aviones (Aircraft)."""
    if not request.user.is_staff:
        messages.error(request, "Acceso denegado. Se requiere ser administrador.")
        return redirect('flights:index')
    
    aircrafts = Aircraft.objects.all().order_by('registration_number')
    context = {'aircrafts': aircrafts}
    return render(request, 'flights/manage_aircrafts.html', context)

@login_required
def create_aircraft(request):
    """Permite al administrador crear un nuevo avión."""
    if not request.user.is_staff:
        messages.error(request, "Acceso denegado. Se requiere ser administrador.")
        return redirect('flights:index')
    
    if request.method == 'POST':
        form = AircraftManagementForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Avión creado exitosamente.")
            return redirect('flights:manage_aircrafts')
    else:
        form = AircraftManagementForm()
        
    context = {'form': form, 'page_title': 'Agregar Nuevo Avión'}
    # Nota: Asegúrate de tener la plantilla 'flights/aircraft_form.html'
    return render(request, 'flights/aircraft_form.html', context)

@login_required
def edit_aircraft(request, aircraft_id):
    """Permite al administrador editar un avión existente."""
    if not request.user.is_staff:
        messages.error(request, "Acceso denegado. Se requiere ser administrador.")
        return redirect('flights:index')
    
    aircraft = get_object_or_404(Aircraft, pk=aircraft_id)
    
    if request.method == 'POST':
        form = AircraftManagementForm(request.POST, instance=aircraft)
        if form.is_valid():
            form.save()
            messages.success(request, f"Avión {aircraft.registration_number} actualizado exitosamente.")
            return redirect('flights:manage_aircrafts')
    else:
        form = AircraftManagementForm(instance=aircraft)
        
    context = {'form': form, 'page_title': f'Editar Avión {aircraft.registration_number}', 'aircraft': aircraft}
    return render(request, 'flights/aircraft_form.html', context)

@login_required
def delete_aircraft(request, aircraft_id):
    """Permite al administrador eliminar un avión."""
    if not request.user.is_staff:
        messages.error(request, "Acceso denegado. Se requiere ser administrador.")
        return redirect('flights:index')

    aircraft = get_object_or_404(Aircraft, pk=aircraft_id)

    if request.method == 'POST':
        # VERIFICACIÓN DE INTEGRIDAD: No eliminar si hay vuelos asociados
        if aircraft.flight_set.exists():
            messages.error(request, f"No se puede eliminar el avión {aircraft.registration_number} porque tiene vuelos asignados. Elimine los vuelos primero.")
        else:
            aircraft.delete()
            messages.success(request, f"Avión {aircraft.registration_number} eliminado exitosamente.")
            
    return redirect('flights:manage_aircrafts')

# =========================================================
# VISTAS DE ADMINISTRACIÓN DE BOLETOS (CRUD)
# =========================================================

@login_required
def manage_tickets(request):
    """Muestra la lista de boletos."""
    if not request.user.is_staff:
        messages.error(request, "Acceso denegado.")
        return redirect('flights:index')
    
    tickets = Ticket.objects.select_related('reservation__flight', 'reservation__passenger').all().order_by('-reservation__flight__departure_time')
    context = {'tickets': tickets}
    return render(request, 'flights/manage_tickets.html', context)

@login_required
def create_ticket(request):
    """Permite al administrador crear un nuevo boleto."""
    if not request.user.is_staff:
        messages.error(request, "Acceso denegado.")
        return redirect('flights:index')
    
    if request.method == 'POST':
        form = TicketManagementForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Boleto creado exitosamente.")
            return redirect('flights:manage_tickets')
    else:
        form = TicketManagementForm()
        
    context = {'form': form, 'page_title': 'Crear Nuevo Boleto'}
    return render(request, 'flights/ticket_form.html', context)

@login_required
def edit_ticket(request, ticket_id):
    """Permite al administrador editar un boleto existente."""
    if not request.user.is_staff:
        messages.error(request, "Acceso denegado.")
        return redirect('flights:index')
    
    ticket = get_object_or_404(Ticket, pk=ticket_id)
    
    if request.method == 'POST':
        form = TicketManagementForm(request.POST, instance=ticket)
        if form.is_valid():
            form.save()
            messages.success(request, f"Boleto #{ticket.id} actualizado exitosamente.")
            return redirect('flights:manage_tickets')
    else:
        form = TicketManagementForm(instance=ticket)
        
    context = {'form': form, 'page_title': f'Editar Boleto #{ticket.id}', 'ticket': ticket}
    return render(request, 'flights/ticket_form.html', context)

@login_required
def delete_ticket(request, ticket_id):
    """Permite al administrador eliminar un boleto."""
    if not request.user.is_staff:
        messages.error(request, "Acceso denegado.")
        return redirect('flights:index')

    if request.method == 'POST':
        ticket = get_object_or_404(Ticket, pk=ticket_id)
        try:
            ticket.delete()
            messages.success(request, f"Boleto #{ticket_id} eliminado exitosamente.")
        except Exception as e:
            messages.error(request, f"Error al eliminar el boleto: {e}")
            
    return redirect('flights:manage_tickets')

# =========================================================
# VISTAS DE ADMINISTRACIÓN DE RESERVAS (CRUD)
# =========================================================

@login_required
def manage_reservations(request):
    """Muestra la lista de reservas."""
    if not request.user.is_staff:
        messages.error(request, "Acceso denegado.")
        return redirect('flights:index')
    
    reservations = Reservation.objects.select_related('flight', 'passenger').all().order_by('-booking_date')
    context = {'reservations': reservations}
    return render(request, 'flights/manage_reservations.html', context)

@login_required
def create_reservation(request): # <-- ESTA FUNCIÓN FALTABA O ESTABA MAL NOMBRADA
    """Permite al administrador crear una nueva reserva."""
    if not request.user.is_staff:
        messages.error(request, "Acceso denegado.")
        return redirect('flights:index')
    
    if request.method == 'POST':
        # Asegúrate de usar el formulario de gestión correcto aquí:
        form = ReservationManagementForm(request.POST) 
        if form.is_valid():
            form.save()
            messages.success(request, "Reserva creada exitosamente.")
            return redirect('flights:manage_reservations')
    else:
        form = ReservationManagementForm()
        
    context = {'form': form, 'page_title': 'Crear Nueva Reserva'}
    # Asegúrate de tener la plantilla 'flights/reservation_form.html'
    return render(request, 'flights/reservation_form.html', context)

@login_required
def edit_reservation(request, reservation_id):
    """Permite al administrador editar una reserva existente."""
    if not request.user.is_staff:
        messages.error(request, "Acceso denegado.")
        return redirect('flights:index')
    
    reservation = get_object_or_404(Reservation, pk=reservation_id)
    
    if request.method == 'POST':
        form = ReservationManagementForm(request.POST, instance=reservation)
        if form.is_valid():
            form.save()
            messages.success(request, f"Reserva #{reservation_id} actualizada exitosamente.")
            return redirect('flights:manage_reservations')
    else:
        form = ReservationManagementForm(instance=reservation)
        
    context = {'form': form, 'page_title': f'Editar Reserva #{reservation_id}', 'reservation': reservation}
    return render(request, 'flights/reservation_form.html', context)

@login_required
def delete_reservation(request, reservation_id):
    """Permite al administrador eliminar una reserva."""
    if not request.user.is_staff:
        messages.error(request, "Acceso denegado.")
        return redirect('flights:index')

    if request.method == 'POST':
        reservation = get_object_or_404(Reservation, pk=reservation_id)

        try:
            associated_ticket = reservation.ticket
            
            messages.error(request, f"No se puede eliminar la reserva #{reservation_id} porque ya tiene el boleto {associated_ticket.ticket_code} asociado.")
            
        except AttributeError:
            try:
                reservation.delete()
                messages.success(request, f"Reserva #{reservation_id} eliminada exitosamente.")
            except Exception as e:
                messages.error(request, f"Error al eliminar la reserva: {e}")
            
    return redirect('flights:manage_reservations')

# =========================================================
# VISTAS DE ADMINISTRACIÓN DE ASIENTOS (CRUD)
# =========================================================

@login_required
def manage_seats(request):
    """Muestra la lista de asientos (Seat)."""
    if not request.user.is_staff:
        messages.error(request, "Acceso denegado. Se requiere ser administrador.")
        return redirect('flights:index')
    
    seats = Seat.objects.select_related('aircraft').all().order_by('aircraft__registration_number', 'seat_number')
    context = {'seats': seats}
    return render(request, 'flights/manage_seats.html', context)

@login_required
def create_seat(request):
    """Permite al administrador crear un nuevo asiento."""
    if not request.user.is_staff:
        messages.error(request, "Acceso denegado. Se requiere ser administrador.")
        return redirect('flights:index')
    
    if request.method == 'POST':
        form = SeatManagementForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Asiento creado exitosamente.")
            return redirect('flights:manage_seats')
    else:
        form = SeatManagementForm()
        
    context = {'form': form, 'page_title': 'Agregar Nuevo Asiento'}
    return render(request, 'flights/seat_form.html', context)

@login_required
def edit_seat(request, seat_id):
    """Permite al administrador editar un asiento existente."""
    if not request.user.is_staff:
        messages.error(request, "Acceso denegado. Se requiere ser administrador.")
        return redirect('flights:index')
    
    seat = get_object_or_404(Seat, pk=seat_id)
    
    if request.method == 'POST':
        form = SeatManagementForm(request.POST, instance=seat)
        if form.is_valid():
            form.save()
            messages.success(request, f"Asiento {seat.seat_number} actualizado exitosamente.")
            return redirect('flights:manage_seats')
    else:
        form = SeatManagementForm(instance=seat)
        
    context = {'form': form, 'page_title': f'Editar Asiento {seat.seat_number}', 'seat': seat}
    return render(request, 'flights/seat_form.html', context)

@login_required
def delete_seat(request, seat_id):
    """Permite al administrador eliminar un asiento."""
    if not request.user.is_staff:
        messages.error(request, "Acceso denegado. Se requiere ser administrador.")
        return redirect('flights:index')

    seat = get_object_or_404(Seat, pk=seat_id)

    if request.method == 'POST':
        if seat.reservation_set.exists():
            messages.error(request, f"No se puede eliminar el asiento {seat.seat_number} porque está asociado a una o más reservas.")
        else:
            seat.delete()
            messages.success(request, f"Asiento {seat.seat_number} eliminado exitosamente.")
            
    return redirect('flights:manage_seats')

# Vistas CRUD para pasajeros
class PassengerListView(AdminRequiredMixin, ListView):
    model = Passenger
    template_name = 'flights/manage_passengers.html'
    context_object_name = 'passengers'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Gestión de Pasajeros'
        return context

class PassengerCreateView(AdminRequiredMixin, SuccessMessageMixin, CreateView):
    model = Passenger
    form_class = PassengerManagementForm
    template_name = 'flights/passenger_form.html'
    success_url = reverse_lazy('flights:manage_passengers')
    success_message = "Pasajero '%(last_name)s, %(first_name)s' creado exitosamente."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Crear Nuevo Pasajero'
        return context

class PassengerUpdateView(AdminRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Passenger
    form_class = PassengerManagementForm
    template_name = 'flights/passenger_form.html'
    success_url = reverse_lazy('flights:manage_passengers')
    success_message = "Pasajero '%(last_name)s, %(first_name)s' actualizado exitosamente."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Editar Pasajero'
        return context

class PassengerDeleteView(AdminRequiredMixin, SuccessMessageMixin, DeleteView):
    model = Passenger
    template_name = 'flights/_confirm_delete.html' 
    success_url = reverse_lazy('flights:manage_passengers')
    success_message = "Pasajero eliminado exitosamente."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['object'] = self.object 
        return context
# =========================================================
# VISTAS DE ADMINISTRACIÓN DE BOLETOS/TICKETS (CRUD)
# =========================================================

@login_required
def manage_tickets(request):
    """Muestra la lista de boletos (Tickets)."""
    if not request.user.is_staff:
        messages.error(request, "Acceso denegado. Se requiere ser administrador.")
        return redirect('flights:index')
    
    # Usamos select_related para minimizar consultas, accediendo a Reservation, Flight y Passenger
    tickets = Ticket.objects.select_related(
        'reservation', 
        'reservation__flight', 
        'reservation__passenger'
    ).all().order_by('-reservation__flight__departure_time')
    
    context = {'tickets': tickets}
    return render(request, 'flights/manage_tickets.html', context)

@login_required
def create_ticket(request):
    """Permite al administrador crear un nuevo boleto."""
    if not request.user.is_staff:
        messages.error(request, "Acceso denegado. Se requiere ser administrador.")
        return redirect('flights:index')
    
    page_title = 'Agregar Nuevo Boleto' # Define el título aquí para el contexto

    if request.method == 'POST':
        form = TicketManagementForm(request.POST)
        if form.is_valid():
            ticket = form.save()  
            
            messages.success(request, f"Boleto {ticket.ticket_code} creado exitosamente.")
            return redirect('flights:manage_tickets')
    else:
        form = TicketManagementForm()
        
    context = {'form': form, 'page_title': page_title}
    return render(request, 'flights/ticket_form.html', context)

@login_required
def edit_ticket(request, ticket_id):
    """Permite al administrador editar un boleto existente."""
    if not request.user.is_staff:
        messages.error(request, "Acceso denegado. Se requiere ser administrador.")
        return redirect('flights:index')
    
    ticket = get_object_or_404(Ticket, pk=ticket_id)
    
    if request.method == 'POST':
        form = TicketManagementForm(request.POST, instance=ticket)
        if form.is_valid():
            form.save()
            messages.success(request, f"Boleto {ticket.ticket_code} actualizado exitosamente.")
            return redirect('flights:manage_tickets')
    else:
        form = TicketManagementForm(instance=ticket)
        
    context = {'form': form, 'page_title': f'Editar Boleto {ticket.ticket_code}', 'ticket': ticket}
    return render(request, 'flights/ticket_form.html', context)

@login_required
def delete_ticket(request, ticket_id):
    # Solo permite la eliminación si el método es POST (seguridad)
    if request.method == 'POST':
        ticket = get_object_or_404(Ticket, pk=ticket_id)
        
        try:
            # Lógica de negocio (opcional):
            # Si el boleto ya se usó (check-in), no se elimina, solo se cancela.
            if ticket.is_checked_in:
                 messages.error(request, "El boleto no se puede eliminar, ya fue usado.")
                 return redirect('flights:ticket_list') 

            # Eliminación del boleto
            ticket.delete()
            messages.success(request, f"Boleto {ticket.ticket_code} eliminado correctamente.")
            
        except Exception as e:
            # Manejo de cualquier error inesperado
            messages.error(request, f"Error al intentar eliminar el boleto: {e}")

    return redirect('flights:manage_tickets')

# ----------------------------------------------------
# VISTAS DE GESTIÓN DE CUENTAS DE USUARIO (ADMIN CRUD)
# ----------------------------------------------------

class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Mixin que requiere que el usuario esté logueado y sea staff (administrador).
    """
    def test_func(self):
        return self.request.user.is_staff
    def handle_no_permission(self):
        messages.error(self.request, "Acceso denegado. Solo personal autorizado.")
        return redirect('flights:index')

class UserListView(AdminRequiredMixin, ListView):
    model = User
    template_name = 'flights/manage_users.html'
    context_object_name = 'users'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Gestión de Cuentas de Usuario'
        return context

class UserCreateView(AdminRequiredMixin, SuccessMessageMixin, CreateView):
    model = User
    form_class = UserManagementForm
    template_name = 'flights/user_form.html'
    success_url = reverse_lazy('flights:manage_users')
    success_message = "Usuario '%(username)s' creado exitosamente."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Crear Nuevo Usuario'
        return context

class UserUpdateView(AdminRequiredMixin, SuccessMessageMixin, UpdateView):
    model = User
    form_class = UserUpdateForm
    template_name = 'flights/user_form.html'
    success_url = reverse_lazy('flights:manage_users')
    success_message = "Usuario '%(username)s' actualizado exitosamente."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Editar Usuario'
        return context

class UserDeleteView(AdminRequiredMixin, SuccessMessageMixin, DeleteView):
    model = User
    template_name = 'flights/_confirm_delete.html' 
    success_url = reverse_lazy('flights:manage_users')
    success_message = "Usuario eliminado exitosamente."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['object'] = self.object
        return context

# Mixin para asegurar que solo los administradores accedan a la gestión
class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Requiere que el usuario esté logueado y sea staff (admin)."""
    def test_func(self):
        # Asumiendo que is_staff determina los permisos de gestión
        return self.request.user.is_staff

# --- VISTAS CRUD DE VUELOS ---

class FlightListView(StaffRequiredMixin, ListView):
    """Muestra el listado de todos los vuelos."""
    model = Flight
    template_name = 'flights/dashboard/flight_list.html'
    context_object_name = 'flights'
    ordering = ['departure_time']

class FlightCreateView(StaffRequiredMixin, CreateView):
    """Maneja la creación de nuevos vuelos."""
    model = Flight
    form_class = FlightManagementForm
    template_name = 'flights/dashboard/flight_form.html'
    # Redirige a la lista después de crear
    success_url = reverse_lazy('flights:flight_list') 

class FlightUpdateView(StaffRequiredMixin, UpdateView):
    """Maneja la edición de un vuelo existente."""
    model = Flight
    form_class = FlightManagementForm
    template_name = 'flights/dashboard/flight_form.html'
    success_url = reverse_lazy('flights:flight_list')

class FlightDeleteView(StaffRequiredMixin, DeleteView):
    """Maneja la confirmación y eliminación de un vuelo."""
    model = Flight
    template_name = 'flights/dashboard/flight_confirm_delete.html'
    success_url = reverse_lazy('flights:flight_list')

class FlightSeatManagementView(StaffRequiredMixin, View):
    """Muestra el plano de asientos de un vuelo y permite la gestión/reserva."""
    template_name = 'flights/dashboard/flight_seat_management.html'

    def get(self, request, pk):
        flight = get_object_or_404(Flight, pk=pk)
        aircraft = flight.aircraft

        # Obtener todos los asientos del avión
        all_seats = Seat.objects.filter(aircraft=aircraft).order_by('seat_number')

        # Determinar qué asientos están reservados para ESTE vuelo
        # Utilizamos un Subquery/Exists para eficiencia (similar a la lógica de la API)
        reserved_seats = all_seats.annotate(
            is_reserved=Exists(
                Reservation.objects.filter(
                    flight=flight,
                    seat=OuterRef('pk'),
                    is_confirmed=True # Solo consideramos reservas confirmadas
                )
            )
        )
        
        # Opcionalmente, puedes agrupar los asientos por filas o simplemente pasarlos
        context = {
            'flight': flight,
            'aircraft': aircraft,
            'seats': reserved_seats,
            # Añade lógica para agrupar por filas si tu Seat tiene campo 'row'
        }
        return render(request, self.template_name, context)

    # También podrías añadir un método POST para manejar la reserva/cancelación directa
    # if request.method == 'POST': ...

def book_flight(request, flight_id):
    flight = get_object_or_404(Flight, pk=flight_id)
    
    # 1. LÓGICA DE PROCESAMIENTO DEL FORMULARIO
    if request.method == 'POST':
        form = ReservationForm(request.POST)
        if form.is_valid():
            # 2. GUARDAR LA RESERVA
            reservation = form.save(commit=False)
            reservation.flight = flight  # Asigna el vuelo actual a la reserva
            # Aquí podrías asignar el usuario actual: reservation.user = request.user
            reservation.save()
            
            # 3. REDIRECCIONAR a una página de confirmación o detalle
            # Debes tener una URL llamada 'reservation_detail' que acepte el ID de la reserva.
            return redirect('flights:reservation_detail', reservation_id=reservation.id)
    
    # 4. CREAR EL FORMULARIO VACÍO (GET request o si el formulario no es válido)
    else:
        form = ReservationForm()
        
    context = {
        'flight': flight,
        'form': form,
        'page_title': f"Reservar Vuelo: {flight.origin} a {flight.destination}"
    }
    
    return render(request, 'flights/book_flight.html', context)

def register_customer(request):
    if request.method == 'POST':
        form = CustomerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Opcional: Inicia sesión automáticamente después del registro
            login(request, user) 
            
            # Redirigir a la página principal o a la página de búsqueda
            return redirect('flights:index') 
    else:
        form = CustomerRegistrationForm()
        
    context = {
        'form': form,
        'page_title': 'Registro de Nuevo Cliente'
    }
    return render(request, 'flights/register.html', context)