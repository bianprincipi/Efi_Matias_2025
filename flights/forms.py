from django import forms
from .models import Reservation, Flight, Seat, Passenger, Ticket


# 1. Formulario de Búsqueda de Vuelos
class FlightSearchForm(forms.Form):
    """Formulario para filtrar vuelos por origen, destino y fecha."""
    
    # Eliminamos las líneas de consulta directa de la base de datos aquí.

    # Definimos los campos como variables de clase
    origin = forms.ChoiceField(
        choices=[], # Lo inicializamos vacío
        required=False,
        label="Origen",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    destination = forms.ChoiceField(
        choices=[], # Lo inicializamos vacío
        required=False,
        label="Destino",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    date = forms.DateField(
        required=False,
        label="Fecha de Salida",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 💥 ESTA LÓGICA SOLO SE EJECUTA CUANDO SE CREA UNA INSTANCIA DEL FORMULARIO 💥
        try:
            # 1. Obtener ciudades
            cities = Flight.objects.values_list('origin', 'destination').distinct()
            
            # Combinar orígenes y destinos en un conjunto para obtener opciones únicas
            unique_cities = set()
            for origin, destination in cities:
                unique_cities.add(origin)
                unique_cities.add(destination)
            
            # Crear la lista de opciones
            CITY_CHOICES = sorted([(city, city) for city in unique_cities])
            CITY_CHOICES.insert(0, ('', '--- Todos ---'))
            
            # 2. Asignar las opciones a los campos
            self.fields['origin'].choices = CITY_CHOICES
            self.fields['destination'].choices = CITY_CHOICES
            
        except Exception as e:
            # Si hay un error (ej. tabla no existe), no hacemos nada y dejamos la lista vacía.
            # print(f"DEBUG: Error al cargar ciudades: {e}") 
            pass

# 2. Formulario para la Creación de Reservas
class ReservationForm(forms.ModelForm):
    """Formulario para crear una nueva reserva."""
    
    # Campo oculto para pasar el ID del vuelo
    flight_id = forms.IntegerField(widget=forms.HiddenInput(), required=False)
    
    class Meta:
        model = Reservation
        # Solo necesitamos que el usuario seleccione el pasajero y el asiento. 
        # El campo 'flight' y 'reservation_code' se establecen en la vista/modelo.
        fields = ['passenger', 'seat'] 
        
        widgets = {
            'passenger': forms.Select(attrs={'class': 'form-control'}),
            'seat': forms.RadioSelect(attrs={'class': 'list-unstyled'}),
        }
        
    def __init__(self, *args, **kwargs):
        # Capturamos el objeto Flight que se pasa desde la vista (flight_detail)
        current_flight = kwargs.pop('flight', None)
        super().__init__(*args, **kwargs)

        if current_flight:
            # 1. Filtramos el campo 'seat' para que solo muestre asientos del avión de este vuelo.
            # (El queryset de asientos disponibles finales se establece en views.py)
            self.fields['seat'].queryset = Seat.objects.filter(aircraft=current_flight.aircraft)
            
            # 2. Establecemos el valor inicial para el campo oculto
            self.initial['flight_id'] = current_flight.id
            
        # Opcional: Podemos mejorar la lista de pasajeros (por si hay muchos)
        self.fields['passenger'].queryset = Passenger.objects.all().order_by('last_name')
        
    def clean_seat(self):
        """Validación adicional para asegurar que el asiento esté realmente disponible."""
        seat = self.cleaned_data.get('seat')
        
        # Recuperamos el ID del vuelo del campo oculto
        flight_id = self.initial.get('flight_id') or self.data.get('flight_id')
        
        if not flight_id:
            raise forms.ValidationError("Error interno: Falta el ID del vuelo.")
        
        # Verificamos si el asiento ya está reservado en este vuelo
        if Reservation.objects.filter(flight_id=flight_id, seat=seat).exists():
            # Esta es una doble verificación, ya que la vista debería filtrar esto, pero es más seguro.
            raise forms.ValidationError("El asiento seleccionado ya ha sido reservado. Por favor, elige otro.")
        
        return seat

class FlightForm(forms.ModelForm):
    """
    Formulario basado en el modelo Flight para Crear y Editar.
    """
    class Meta:
        model = Flight
        fields = ['flight_number', 'origin', 'destination', 'departure_time', 'arrival_time', 'price', 'aircraft']
        
        # Personalización de widgets
        widgets = {
            'flight_number': forms.TextInput(attrs={'class': 'form-control'}),
            'origin': forms.TextInput(attrs={'class': 'form-control'}),
            'destination': forms.TextInput(attrs={'class': 'form-control'}),
            'departure_time': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'arrival_time': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'min': '0', 'step': '0.01', 'class': 'form-control'}), # <-- ¡CORREGIDO!
            'aircraft': forms.Select(attrs={'class': 'form-control'}),
        }

# =========================================================
# FORMULARIO DE GESTIÓN DE RESERVAS (CRUD ADMINISTRACIÓN)
# =========================================================
class ReservationManagementForm(forms.ModelForm):
    """
    Formulario para Crear y Editar Reservas (usado por el administrador en el Dashboard).
    """
    class Meta:
        model = Reservation
        # ELIMINA 'booking_date' de esta lista.
        fields = ['flight', 'passenger', 'seat', 'is_confirmed']
        
        widgets = {
            'flight': forms.Select(attrs={'class': 'form-control'}),
            'passenger': forms.Select(attrs={'class': 'form-control'}),
            'seat': forms.Select(attrs={'class': 'form-control'}), 
            'is_confirmed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            # ELIMINA el widget de 'booking_date'
            # 'booking_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Opcional: Mejorar los querysets si hay muchos registros
        self.fields['passenger'].queryset = Passenger.objects.all().order_by('last_name')
        self.fields['flight'].queryset = Flight.objects.all().order_by('-departure_time')


# =========================================================
# FORMULARIO DE GESTIÓN DE BOLETOS/TICKETS (CRUD ADMINISTRACIÓN)
# =========================================================
class TicketManagementForm(forms.ModelForm):
    """
    Formulario para Crear y Editar Boletos (usado por el administrador en el Dashboard).
    """
    class Meta:
        model = Ticket
        # Un boleto solo necesita ser asociado a una Reserva y tiene un estado de check-in.
        fields = ['reservation', 'is_checked_in'] 
        
        widgets = {
            'reservation': forms.Select(attrs={'class': 'form-control'}),
            'is_checked_in': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        
    def clean_ticket_code(self):
        """Asegura que el código se autogenere si es un registro nuevo y el campo está vacío."""
        ticket_code = self.cleaned_data.get('ticket_code')
        if not self.instance.pk and not ticket_code:
            # Si es un objeto nuevo y el código está vacío, genera uno.
            # Nota: Esto debería manejarlo mejor el modelo/servicio si usas UUID, 
            # pero lo forzamos aquí para el formulario.
            import uuid
            ticket_code = str(uuid.uuid4()).split('-')[-1].upper()
        
        return ticket_code