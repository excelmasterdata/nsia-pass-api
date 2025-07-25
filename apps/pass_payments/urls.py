# apps/pass_payments/urls.py
from django.urls import path
from . import views

app_name = 'pass_payments'

urlpatterns = [
    #  NOUVEAUX ENDPOINTS FLEXIBLES
    path('initier/', views.initier_paiement_flexible, name='initier_paiement_flexible'),
    path('operateurs/', views.operateurs_supportes, name='operateurs_supportes'),
    path('detecter-operateur/', views.detecter_operateur, name='detecter_operateur'),
    
    # Statut et historique (compatible avec tous les opérateurs)
    path('statut/<str:numero_transaction>/', views.verifier_statut_paiement_borne, name='statut_paiement'),
    path('historique/<str:police>/', views.historique_paiements_client, name='historique_paiements'),
    
    #  ANCIENS ENDPOINTS (rétrocompatibilité)
    path('mtn/initier/', views.initier_paiement_borne, name='initier_paiement_mtn'),
    
    # Nouvelles souscriptions avec choix d'opérateur
    path('nouvelle-souscription/', views.nouvelle_souscription_avec_paiement, name='nouvelle_souscription'),

    # CALLBACK MTN PERSONNALISE
    path("mtn/callback/", views.mtn_callback, name="mtn_callback"),
]