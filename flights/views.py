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
from django_filters.rest_framework import DjangoFilterBackend  
from .models import Flight, Passenger, Reservation, Seat, Ticket, Aircraft 
from .serializers import (
    VueloSerializer, 
    PassengerSerializer, 
    ReservationSerializer, 
    AircraftSerializer,
    SeatSerializer,
    TicketSerializer    
) 
import uuid #generar codigo de barras
from .services.ticket_servide import TicketService
from django.contrib.admin.views.decorators import staff_member_required
import random


def index(request):
    """
        Controlador principal que diferencia entre Cliente y Administrador.
    """
    # Si el usuario está autenticado y es personal, redirigirlo al dashboard (Descomentar si usas autenticación)
    # if request.user.is_authenticated and request.user.is_staff:
    #     return redirect('admin_dashboard')
    
    # Muestra la página de búsqueda con algunos vuelos iniciales (solo los primeros 5)
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
    """
        Procesa el formulario de búsqueda de vuelos y muestra los resultados.
    """
    results = Flight.objects.none() # Inicializa un QuerySet vacío
    
    # Instanciamos el formulario con los datos GET
    form = FlightSearchForm(request.GET)
    
    if form.is_valid():
        # Obtener datos limpios
        origin = form.cleaned_data.get('origin')
        destination = form.cleaned_data.get('destination')
        date = form.cleaned_data.get('date')
        
        # Base de la consulta
        queryset = Flight.objects.all()
        
        # 1. Filtrar por Origen
        if origin:
            # Filtra por el valor exacto del origen (nombre de la ciudad)
            queryset = queryset.filter(origin=origin) 
        
        # 2. Filtrar por Destino
        if destination:
            queryset = queryset.filter(destination=destination)
        
        # 3. Filtrar por Fecha (solo el día)
        if date:
            # Filtra por la parte de la fecha del campo datetime
            queryset = queryset.filter(departure_time__date=date)
            
        # Ejecutar y ordenar los resultados
        results = queryset.order_by('departure_time')

    context = {
        'search_form': form, # Pasamos el formulario con los datos de búsqueda de vuelta
        'results': results,  # Los vuelos encontrados
        'page_title': "Resultados de Búsqueda"
    }
    
    # Renderizamos la plantilla search_results.html
    return render(request, 'flights/search_results.html', context)

def flight_detail(request, flight_id):
    """
    Muestra los detalles de un vuelo específico, el plano de asientos
    y maneja la creación de una reserva (POST).
    """
    flight = get_object_or_404(Flight, pk=flight_id)
    aircraft = flight.aircraft

    # Obtener IDs de asientos ya reservados para este vuelo
    reserved_seat_ids = Reservation.objects.filter(flight=flight).values_list('seat_id', flat=True)
    
    # Obtener todos los asientos de la aeronave
    all_seats = Seat.objects.filter(aircraft=aircraft).order_by('row_number', 'letter')

    # 1. Manejar el envío del formulario de reserva (POST)
    if request.method == 'POST':
        # Instanciamos el ReservationForm, pasándole el objeto Flight para filtrar asientos
        form = ReservationForm(request.POST, flight=flight)
        
        if form.is_valid():
            # Generar código de reserva aleatorio de 6 caracteres
            code = ''.join(random.choices('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=6))

            # Crear la nueva reserva (pero no guardar todavía)
            reservation = form.save(commit=False)
            reservation.flight = flight
            reservation.reservation_code = code
            
            # Guardar la reserva
            reservation.save()
            
            # Redirigir a una página de confirmación o de inicio
            return redirect('index') # Puedes cambiar esto a una página de confirmación
        
    # 2. Manejar la solicitud inicial (GET)
    else:
        # Instanciamos el formulario de reserva, pasándole el objeto Flight para inicializar campos
        form = ReservationForm(flight=flight)
        
        # Filtramos el queryset de asientos del formulario para mostrar solo los disponibles
        # Usamos .exclude() para quitar los IDs reservados
        form.fields['seat'].queryset = all_seats.exclude(id__in=reserved_seat_ids)

    # Organizar asientos para la visualización del plano
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
        if self.action in ['list', 'retrieve', 'pasajeros']:
            permission_classes = [AllowAny] 
        else:
            permission_classes = [IsAirlineAdmin] 
        
        return [permission() for permission in permission_classes]
    
    @action(detail=True, methods=['get'], url_path='pasajeros', permission_classes=[AllowAny])
    def pasajeros(self, request, pk=None):
        """Devuelve todos los pasajeros que tienen una reserva confirmada para este vuelo."""
        flight = self.get_object() 

        #filtramos por reservas confirmadas
        reservations = Reservation.objects.filter(
            flight=flight,
            estado__in=['CONFIRMADA', 'EMITIDO']
        ).select_related('passenger')

        #solo los pasajeros
        passengers = [res.passenger for res in reservations]

        #usamos el passengerserializer para serializar la lista de pasajeros
        serializer = PassengerSerializer(passengers, many=True) 

        return Response({
            "vuelo": flight.flight_number,
            "total_pasajeros_activos": len(passengers),
            "pasajeros": serializer.data
        })


class PassengerViewSet(viewsets.ModelViewSet):
    """
    ViewSet para la Gestión de Pasajeros. 
    Permite: Registrar (POST), Detalle (GET /<id>), y Listar Reservas asociadas.
    Endpoints: /api/pasajeros/
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
        """Devuelve solo las reservas activas (confirmadas o pendientes) de un pasajero."""
        passenger = self.get_object() 
        
        # Filtramos por estados considerados "activos"
        active_states = ['PENDIENTE', 'CONFIRMADA', 'EMITIDO'] 
        
        active_reservations = Reservation.objects.filter(
            passenger=passenger, 
            # ⚠️ Ajustar 'estado' al campo real de tu modelo
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
    Permite: Crear (POST /api/reservas/), Detalle (GET /api/reservas/<id>/) y Cambiar Estado (PATCH /api/reservas/<id>/estado/).
    """
    queryset = Reservation.objects.all()
    serializer_class = ReservationSerializer
    
    def get_permissions(self):
        permission_classes = [IsAirlineAdmin] 
        return [permission() for permission in permission_classes]

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

    @action(detail=True, methods=['patch'], url_path='estado', permission_classes=[AllowAny])
    def cambiar_estado(self, request, pk=None):
        """Permite cambiar el estado de la reserva (ej. 'CONFIRMADA', 'CANCELADA')."""
        
        reservation = self.get_object()
        new_state = request.data.get('estado')

        if not new_state:
            return Response({"error": "Debe proporcionar el nuevo estado de la reserva ('estado')."}, 
                            status=status.HTTP_400_BAD_REQUEST)
        
        try:
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
        if self.action in ['list', 'retrieve', 'layout', 'disponibilidad']:
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAirlineAdmin]
        return [permission() for permission in permission_classes]

    @action(detail=True, methods=['get'])
    def layout(self, request, pk=None):
        """Devuelve todos los asientos asociados al avión."""
        aircraft = self.get_object()
        seats = aircraft.seats.all().order_by('seat_number') 
        serializer = SeatSerializer(seats, many=True) 
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
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
    ViewSet para la Gestión de Boletos.
    Endpoints: /api/boletos/
    Permite: generar (POST) y consultar por ID o codifo (Retrieve).
    """
    queryset = Ticket.objects.all().select_related('reservation__flight', 'reservation__passenger', 'reservation__seat')
    serializer_class = TicketSerializer
    lookup_field = 'codigo_barra' # Permite buscar por código de barra además del ID.
    
    def get_permissions(self):
        """Permisos: Generar y consultar: usuario autenticado"""
        permission_classes = [IsAirlineAdmin]
        return [permission() for permission in permission_classes]

    @action(detail=False, methods=['post'], url_path='generar')
    def generar(self, request):
        """
        Genera un boleto a partir de una reserva confirmada, delegando toda 
        la lógica de negocio al TicketService.
        """
        reservation_code = request.data.get('reservation_code')
        
        if not reservation_code:
            return Response({"error": "Debe proporcionar el código de reserva ('reservation_code')."}, 
                        status=status.HTTP_400_BAD_REQUEST)
            
        try:
            boleto = TicketService.generate_ticket(reservation_code)
            
            # Si el servicio retorna el boleto, la operación fue exitosa.
            serializer = self.get_serializer(boleto)
            return Response({
                "message": "Boleto generado con éxito.",
                "data": serializer.data
            }, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            # Captura errores de validación del servicio
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            # Captura cualquier otro error inesperado
            return Response({"error": f"Error interno al generar el boleto: {str(e)}"}, 
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

@staff_member_required #solo permite si el usuario ha iniciado sesion y es staff/admin
def admin_dashboard(request):
    """
        Muestra el panel de control del administrador.
    """
    context = {
        'page_title': 'Panel de Administración.'
    }
    return render(request, 'flights/admin_dashboard.html', context)