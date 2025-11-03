from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),

    #conecta lasa urls de la aplicacion fligths
    path('flights/', include('flights.urls')),
]
