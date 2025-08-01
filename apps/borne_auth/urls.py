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

    # Liste et création
    path('agents/', views.AgentListView.as_view(), name='agent_list'),
    path('agents/create/', views.AgentCreateView.as_view(), name='agent_create'),
    
    # Actions sur agent spécifique
    path('agents/<int:pk>/', views.AgentDetailView.as_view(), name='agent_detail'),
    path('agents/<int:pk>/update/', views.AgentUpdateView.as_view(), name='agent_update'),
    path('agents/<int:pk>/delete/', views.AgentDeleteView.as_view(), name='agent_delete'),
    
    # Actions spéciales pour admin
    path('agents/<int:agent_id>/toggle-status/', views.toggle_agent_status, name='toggle_agent_status'),
    path('agents/<int:agent_id>/stats/', views.agent_stats, name='agent_stats'),
    path('agents/dashboard/', views.agents_dashboard, name='agents_dashboard'),
    
    # Authentification agent
    path('auth/agent/login/', views.agent_login, name='agent_login'),
    path('auth/agent/profile/', views.agent_profile, name='agent_profile'),
    path('auth/agent/logout/', views.agent_logout, name='agent_logout'),
    
    
]