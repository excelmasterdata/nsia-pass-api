from django.urls import path, include
from . import views

urlpatterns = [
    # Authentification borne
    path('borne/auth/login/', views.borne_authenticate, name='borne_login'),
    
    # Dashboard et données client
    path('clients/<str:police>/dashboard/', views.client_dashboard, name='client_dashboard'),
    path('clients/<str:police>/contrats/', views.client_contrats, name='client_contrats'),
    path('clients/<str:police>/cotisations/', views.client_cotisations, name='client_cotisations'),
    # Paiements MTN pour la borne
    path('paiements/', include('apps.pass_payments.urls')),
]