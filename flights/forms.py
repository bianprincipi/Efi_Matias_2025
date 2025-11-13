from django import forms
from django.db import models
from .models import Reservation, Flight, Seat, Passenger, Ticket, Aircraft, Airport
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User

User = get_user_model()

# =========================================================
# 1. FORMULARIO DE BÚSQUEDA DE VUELOS (PÚBLICO)
# =========================================================
class FlightSearchForm(forms.Form):
    """Formulario para filtrar vuelos por origen, destino y fecha."""
    
    origin = forms.ChoiceField(
        choices=[],
        required=False,
        label="Origen",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    destination = forms.ChoiceField(
        choices=[],
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
        
        CITY_CHOICES = [('', '--- Todos ---')] # Inicia siempre con 'Todos'
        
        try:
            active_flights = Flight.objects.filter(status__in=['SCH', 'ACT'])
            
            origins = active_flights.values_list('origin', flat=True)
            destinations = active_flights.values_list('destination', flat=True)
            
            unique_cities = sorted(set(list(origins) + list(destinations)))
            
            for city in unique_cities:
                CITY_CHOICES.append((city, city)) 
            
        except Exception as e:
            print(f"ERROR al cargar selectores de ciudades en FlightSearchForm: {e}")
            pass 
            
        self.fields['origin'].choices = CITY_CHOICES
        self.fields['destination'].choices = CITY_CHOICES

    def clean(self):
        cleaned_data = super().clean()
        origin_id = cleaned_data.get('origin')
        destination_id = cleaned_data.get('destination')

        if origin_id and destination_id and origin_id == destination_id:
            origin_airport = Airport.objects.get(id=origin_id)
            raise forms.ValidationError(
                f"El origen ({origin_airport.city}) y el destino no pueden ser la misma ciudad."
            )
        return cleaned_data

# =========================================================
# 2. FORMULARIO DE RESERVAS (PÚBLICO)
# =========================================================
class ReservationForm(forms.ModelForm):
    """Formulario para crear una nueva reserva (para el cliente)."""
    
    flight_id = forms.IntegerField(widget=forms.HiddenInput(), required=False)
    
    class Meta:
        model = Reservation
        fields = ['passenger', 'seat'] 
        
        widgets = {
            'passenger': forms.Select(attrs={'class': 'form-control'}),
            'seat': forms.RadioSelect(attrs={'class': 'list-unstyled'}),
        }
        
    def __init__(self, *args, **kwargs):
        current_flight = kwargs.pop('flight', None)
        super().__init__(*args, **kwargs)

        if current_flight:
            self.fields['seat'].queryset = Seat.objects.filter(aircraft=current_flight.aircraft)
            self.initial['flight_id'] = current_flight.id
            
        self.fields['passenger'].queryset = Passenger.objects.all().order_by('last_name')
        
    def clean_seat(self):
        """Validación adicional para asegurar que el asiento esté realmente disponible."""
        seat = self.cleaned_data.get('seat')
        
        flight_id = self.initial.get('flight_id') or self.data.get('flight_id')
        
        if not flight_id:
            raise forms.ValidationError("Error interno: Falta el ID del vuelo.")
        
        if Reservation.objects.filter(flight_id=flight_id, seat=seat).exists():
            raise forms.ValidationError("El asiento seleccionado ya ha sido reservado. Por favor, elige otro.")
        
        return seat

# =========================================================
# 3. FORMULARIO DE VUELOS (CRUD ADMINISTRACIÓN)
# =========================================================
class FlightForm(forms.ModelForm):
    """Formulario basado en el modelo Flight para Crear y Editar."""
    class Meta:
        model = Flight
        fields = ['flight_number', 'origin', 'destination', 'departure_time', 'arrival_time', 'price', 'aircraft']
        
        widgets = {
            'flight_number': forms.TextInput(attrs={'class': 'form-control'}),
            'origin': forms.TextInput(attrs={'class': 'form-control'}),
            'destination': forms.TextInput(attrs={'class': 'form-control'}),
            'departure_time': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'arrival_time': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'min': '0', 'step': '0.01', 'class': 'form-control'}),
            'aircraft': forms.Select(attrs={'class': 'form-control'}),
        }

# =========================================================
# 4. FORMULARIO DE PASAJEROS (PÚBLICO/GENÉRICO)
# =========================================================
class PassengerForm(forms.ModelForm):
    class Meta:
        model = Passenger
        fields = [
            'nombre',
            'apellido',
            'email',
            'telefono',
            'tipo_documento', 
            'documento',
            'fecha_nacimiento',
        ] 
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre'}),
            'apellido': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellido'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'ejemplo@correo.com'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Número de teléfono'}),
            'tipo_documento': forms.Select(attrs={'class': 'form-control'}),
            'documento': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Número de Documento/Pasaporte'}),
            'fecha_nacimiento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

# =========================================================
# 5. FORMULARIO DE PASAJEROS (CRUD ADMINISTRACIÓN)
# 🚨 CORRECCIÓN: Usamos los nombres de campos que parecen ser correctos 🚨
# =========================================================
class PassengerManagementForm(forms.ModelForm):
    class Meta:
        model = Passenger
        fields = ('nombre', 'apellido', 'documento', 'tipo_documento', 'email', 'telefono', 'fecha_nacimiento')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fields['nombre'].label = 'Nombre'
        self.fields['apellido'].label = 'Apellido'
        self.fields['documento'].label = 'Número de Documento'
        self.fields['tipo_documento'].label = 'Tipo de Documento'
        self.fields['email'].label = 'Correo Electrónico'
        self.fields['telefono'].label = 'Teléfono'
        self.fields['fecha_nacimiento'].label = 'Fecha de Nacimiento'
        
        self.fields['fecha_nacimiento'].widget = forms.DateInput(attrs={'type': 'date', 'placeholder': 'YYYY-MM-DD', 'class': 'form-control'})
        self.fields['documento'].widget = forms.TextInput(attrs={'class': 'form-control'})
        self.fields['telefono'].widget = forms.TextInput(attrs={'class': 'form-control'})
        self.fields['email'].widget = forms.EmailInput(attrs={'class': 'form-control'})


# =========================================================
# 6. FORMULARIO DE GESTIÓN DE RESERVAS (CRUD ADMINISTRACIÓN)
# =========================================================
class ReservationManagementForm(forms.ModelForm):
    """
    Formulario para Crear y Editar Reservas (usado por el administrador en el Dashboard).
    """
    class Meta:
        model = Reservation
        fields = ['flight', 'passenger', 'seat', 'is_confirmed']
        
        widgets = {
            'flight': forms.Select(attrs={'class': 'form-control'}),
            'passenger': forms.Select(attrs={'class': 'form-control'}),
            'seat': forms.Select(attrs={'class': 'form-control'}), 
            'is_confirmed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['passenger'].queryset = Passenger.objects.all().order_by('last_name')
        self.fields['flight'].queryset = Flight.objects.all().order_by('-departure_time')


# =========================================================
# 7. FORMULARIO DE GESTIÓN DE BOLETOS/TICKETS (CRUD ADMINISTRACIÓN)
# =========================================================
class TicketManagementForm(forms.ModelForm):
    """
    Formulario para Crear y Editar Boletos (usado por el administrador en el Dashboard).
    """
    class Meta:
        model = Ticket
        fields = ['reservation', 'ticket_code'] 
        
        widgets = {
            'reservation': forms.Select(attrs={'class': 'form-control'}),
            'is_checked_in': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'price': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
        } 
        
    def clean_ticket_code(self):
        """Asegura que el código se autogenere si es un registro nuevo y el campo está vacío."""
        ticket_code = self.cleaned_data.get('ticket_code')
        if not self.instance.pk and not ticket_code:
            import uuid
            ticket_code = str(uuid.uuid4()).split('-')[-1].upper()
        
        return ticket_code
    
# =========================================================
# 8. FORMULARIOS DE GESTIÓN DE AVIONES (CRUD ADMINISTRACIÓN)
# =========================================================
class AircraftManagementForm(forms.ModelForm):
    """
    Formulario para Crear y Editar Aviones (usado por el administrador).
    """
    class Meta:
        model = Aircraft
        fields = ['registration_number', 'model', 'capacity', 'rows', 'columns']
        widgets = {
            'registration_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: LV-FUE'}),
            'model': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Boeing 737'}),
            'capacity': forms.NumberInput(attrs={'class': 'form-control', 'min': 10}),
            'rows': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'columns': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
        }

# =========================================================
# 9. FORMULARIOS DE GESTIÓN DE ASIENTOS (CRUD ADMINISTRACIÓN)
# =========================================================
class SeatManagementForm(forms.ModelForm):
    """
    Formulario para Crear y Editar Asientos (usado por el administrador).
    """
    class Meta:
        model = Seat
        fields = ['aircraft', 'seat_number', 'seat_class', 'base_price']
        widgets = {
            'aircraft': forms.Select(attrs={'class': 'form-control'}),
            'seat_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 15A o 45C'}),
            'seat_class': forms.Select(attrs={'class': 'form-control'}),
            'base_price': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': 0.01}),
        }

# =========================================================
# 10. FORMULARIO DE CREACIÓN DE USUARIOS (ADMIN)
# =========================================================
class UserManagementForm(UserCreationForm):
    """
    Formulario utilizado por el administrador para crear nuevos usuarios.
    """
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active')
        
        widgets = {
            'is_staff': forms.CheckboxInput(attrs={'class': 'form-check-input'}), 
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}), 
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fields['username'].label = 'Nombre de Usuario'
        self.fields['email'].label = 'Correo Electrónico'
        self.fields['email'].required = True
        self.fields['first_name'].label = 'Nombre'
        self.fields['last_name'].label = 'Apellido'
        self.fields['is_staff'].label = '¿Es Administrador (Staff)?'
        self.fields['is_active'].label = '¿Está Activo?'

        if 'password2' in self.fields:
            self.fields['password2'].label = 'Confirmación de contraseña'
            self.fields['password2'].help_text = 'Tu contraseña no puede ser similar a tu otra información personal. Debe contener al menos 8 caracteres.'

# =========================================================
# 11. FORMULARIO DE EDICIÓN DE USUARIOS (ADMIN)
# =========================================================
class UserUpdateForm(UserChangeForm):
    """
    Formulario utilizado por el administrador para editar usuarios existentes.
    """
    password = None 

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active')
        
        widgets = {
            'is_staff': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fields['username'].label = 'Nombre de Usuario'
        self.fields['email'].label = 'Correo Electrónico'
        self.fields['email'].required = True
        self.fields['first_name'].label = 'Nombre'
        self.fields['last_name'].label = 'Apellido'
        self.fields['is_staff'].label = '¿Es Administrador (Staff)?'
        self.fields['is_active'].label = '¿Está Activo?'
        
        if 'password' in self.fields:
            del self.fields['password']

class FlightManagementForm(forms.ModelForm):
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
            'origin', 
            'destination', 
            'departure_time', 
            'arrival_time', 
            'price' 
        ]
        labels = {
            'aircraft': 'Avión',
            'flight_number': 'Número de Vuelo',
            'origin': 'Ciudad de Origen',
            'destination': 'Ciudad de Destino',
            'price': 'Precio Base del Vuelo'
        }
        
    def clean(self):
        cleaned_data = super().clean()
        departure = cleaned_data.get('departure_time')
        arrival = cleaned_data.get('arrival_time')
        origin = cleaned_data.get('origin')
        destination = cleaned_data.get('destination')
        
        if departure and arrival and departure >= arrival:
            self.add_error('arrival_time', 'La hora de llegada debe ser posterior a la hora de salida.')

        if origin and destination and origin.lower() == destination.lower():
            self.add_error('destination', 'El origen y el destino no pueden ser la misma ciudad.')
            
        return cleaned_data

class CustomerRegistrationForm(UserCreationForm):
    """
    Formulario personalizado para el registro de nuevos clientes.
    Extiende el UserCreationForm de Django.
    """
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)

    class Meta(UserCreationForm.Meta):
        # Utiliza el modelo User de Django
        model = User
        # Define los campos que se mostrarán en el formulario
        fields = UserCreationForm.Meta.fields + ('email', 'first_name', 'last_name',)

    def clean_email(self):
        # Asegura que el email sea único
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Este email ya está registrado.")
        return email

    def save(self, commit=True):
        # Guardar el usuario y establecer campos adicionales si es necesario
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        
        # Opcionalmente, podrías añadir el usuario a un grupo 'Clientes' aquí
        
        if commit:
            user.save()
        return user