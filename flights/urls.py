# flights/urls.py

from django.urls import path
from . import views 

urlpatterns = [
    # Ruta /flights/
    path('', views.index, name='flight_index'),
    
    # Ruta /flights/search/
    path('search/', views.search_flights, name='search_flights'),
    
    # Ruta /flights/123/
    path('<int:flight_id>/', views.flight_detail, name='flight_detail'),
]