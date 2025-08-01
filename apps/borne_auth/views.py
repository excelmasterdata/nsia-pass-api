from tokenize import TokenError
from rest_framework import status, generics, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Sum, Count, Q
from apps.borne_auth.models import NumeroPolice
from apps.borne_auth.serializers import (AgentLoginSerializer, BorneAuthenticationSerializer, AgentSerializer, AgentCreateSerializer, AgentUpdateSerializer, 
    AgentListSerializer, AgentStatsSerializer)
from apps.pass_clients.models import ClientPass, SouscriptionPass
from apps.pass_payments.models import PaiementPass
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from .models import Agent


@api_view(['POST'])
@permission_classes([AllowAny])
def borne_authenticate(request):
    """
    Authentification pour borne interactive NSIA PASS
    
    POST /api/v1/borne/auth/login/
    {
        "police": "CG-2024-VIE-001",
        "telephone": "+242061234567"
    }
    """
    serializer = BorneAuthenticationSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'message': 'Données invalides',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Données validées
        client = serializer.validated_data['client']
        souscription = serializer.validated_data['souscription']
        numero_police = serializer.validated_data['numero_police']
        
        # Création utilisateur Django temporaire pour JWT
        username = f"borne_client_{client.id}"
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            user = User.objects.create_user(
                username=username,
                email=f"{username}@nsia-borne.cg",
                first_name=client.prenom,
                last_name=client.nom,
            )
        
        # Génération token JWT (session courte pour borne)
        refresh = RefreshToken.for_user(user)
        refresh.set_exp(lifetime=timedelta(minutes=30))  # 30 min max
        
        # Informations client pour la session
        client_data = {
            'client_id': client.id,
            'police': numero_police.numero_police,
            'nom_complet': f"{client.prenom} {client.nom}",
            'telephone': client.telephone,
            'adresse': client.adresse,
            'produit_pass': souscription.produit_pass.nom_pass if souscription.produit_pass else None
        }
        
        # Ajout données personnalisées au token
        refresh['client_id'] = client.id
        refresh['police'] = numero_police.numero_police
        
        return Response({
            'success': True,
            'message': 'Authentification réussie',
            'data': {
                'access_token': str(refresh.access_token),
                'refresh_token': str(refresh),
                'client_info': client_data,
                'session_expires_at': (timezone.now() + timedelta(minutes=30)).isoformat(),
                'session_duration_minutes': 30
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'message': 'Erreur serveur lors de l\'authentification',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def client_dashboard(request, police):
    """
    Dashboard client PASS avec vue d'ensemble
    
    GET /api/v1/clients/{police}/dashboard/
    Headers: Authorization: Bearer <token>
    """
    try:
        # Récupération client via police
        numero_police = NumeroPolice.objects.select_related(
            'souscription_pass__client',
            'souscription_pass__produit_pass'
        ).get(numero_police=police, statut='attribue')
        
        client = numero_police.souscription_pass.client
        
        # Statistiques client
        souscriptions = SouscriptionPass.objects.filter(client=client)
        souscriptions_actives = souscriptions.filter(
            statut__in=['activee']
        ).count()
        
        # Valeur totale des souscriptions
        valeur_totale = PaiementPass.objects.filter(
            client=client,
            statut='succes'
        ).aggregate(total=Sum('montant'))['total'] or 0
        
        # Contrats (vues) basés sur souscriptions avec police
        contrats = []
        polices_client = NumeroPolice.objects.filter(
            souscription_pass__client=client,
            statut='attribue'
        ).select_related('souscription_pass__produit_pass')

        
        for p in polices_client:
            solde_contrat = PaiementPass.objects.filter(
                souscription_pass=p.souscription_pass,
                statut='succes'
            ).aggregate(total=Sum('montant'))['total'] or 0

            contrats.append({
                'police': p.numero_police,
                'produit': p.souscription_pass.produit_pass.nom_pass,
                'montant': solde_contrat,
                'statut': p.souscription_pass.statut,
                'date_souscription': p.souscription_pass.date_souscription,
                'periodicite': p.souscription_pass.periodicite
            })
        
        # Derniers paiements
        derniers_paiements = PaiementPass.objects.filter(
            client=client
        ).order_by('-date_paiement')[:5]
        
        paiements_data = []
        for paiement in derniers_paiements:
            paiements_data.append({
                'numero_transaction': paiement.numero_transaction,
                'montant': paiement.montant,
                'operateur': paiement.operateur,
                'statut': paiement.statut,
                'date_paiement': paiement.date_paiement,
                'type_paiement': paiement.type_paiement
            })
        
        # Dashboard complet
        dashboard_data = {
            'client_info': {
                'nom_complet': f"{client.prenom} {client.nom}",
                'telephone': client.telephone,
                'adresse': client.adresse,
                'date_premiere_souscription': client.date_premiere_souscription
            },
            'statistiques': {
                'souscriptions_actives': souscriptions_actives,
                'total_souscriptions': souscriptions.count(),
                'valeur_totale': valeur_totale,
                'nombre_polices': polices_client.count()
            },
            'contrats': contrats,
            'derniers_paiements': paiements_data
        }
        
        return Response({
            'success': True,
            'data': dashboard_data
        }, status=status.HTTP_200_OK)
        
    except NumeroPolice.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Police introuvable'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'success': False,
            'message': 'Erreur lors de la récupération du dashboard',
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def client_contrats(request, police):
    """
    Liste détaillée des contrats client
    
    GET /api/v1/clients/{police}/contrats/
    """
    try:
        # Tous les contrats du client (basés sur ses souscriptions)
        numero_police_principal = NumeroPolice.objects.select_related(
            'souscription_pass__client'
        ).get(numero_police=police)
        
        client = numero_police_principal.souscription_pass.client
        
        # Toutes les polices du client
        polices_client = NumeroPolice.objects.filter(
            souscription_pass__client=client
        ).select_related(
            'souscription_pass__produit_pass',
            'agent_attribueur'
        ).prefetch_related('souscription_pass__beneficiaires')
        
        contrats_detailles = []
        for p in polices_client:
            souscription = p.souscription_pass
            
            # Bénéficiaires
            beneficiaires = []
            for b in souscription.beneficiaires.all():
                beneficiaires.append({
                    'nom': b.nom,
                    'prenom': b.prenom,
                    'relation': b.relation_souscripteur,
                    'ordre_priorite': b.ordre_priorite
                })
            
            contrats_detailles.append({
                'police': p.numero_police,
                'produit_pass': {
                    'code': souscription.produit_pass.code_pass,
                    'nom': souscription.produit_pass.nom_pass,
                    'categorie': souscription.produit_pass.categorie,
                    'garanties': souscription.produit_pass.garanties
                },
                'souscription': {
                    'numero': souscription.numero_souscription,
                    'montant': souscription.montant_souscription,
                    'periodicite': souscription.periodicite,
                    'statut': souscription.statut,
                    'date_souscription': souscription.date_souscription,
                    'date_activation': souscription.date_activation
                },
                'beneficiaires': beneficiaires,
                'attribution_police': {
                    'date_attribution': p.date_attribution,
                    'mode': p.mode_attribution,
                    'agent': p.agent_attribueur.nom_complet if p.agent_attribueur else None
                }
            })
        
        return Response({
            'success': True,
            'data': {
                'client': f"{client.prenom} {client.nom}",
                'total_contrats': len(contrats_detailles),
                'contrats': contrats_detailles
            }
        }, status=status.HTTP_200_OK)
        
    except NumeroPolice.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Police introuvable'
        }, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
def client_cotisations(request, police):
    """
    Historique des paiements/cotisations client
    
    GET /api/v1/clients/{police}/cotisations/
    """
    try:
        # Client via police
        numero_police = NumeroPolice.objects.select_related(
            'souscription_pass__client'
        ).get(numero_police=police)
        
        client = numero_police.souscription_pass.client
        
        # Tous les paiements du client
        paiements = PaiementPass.objects.filter(
            client=client
        ).select_related('souscription_pass').order_by('-date_paiement')
        
        # Regroupement par type de paiement
        paiements_par_type = {}
        for paiement in paiements:
            type_p = paiement.type_paiement
            if type_p not in paiements_par_type:
                paiements_par_type[type_p] = []
            
            paiements_par_type[type_p].append({
                'numero_transaction': paiement.numero_transaction,
                'montant': paiement.montant,
                'montant_net': paiement.montant_net,
                'frais_transaction': paiement.frais_transaction,
                'operateur': paiement.operateur,
                'numero_payeur': paiement.numero_payeur,
                'statut': paiement.statut,
                'date_paiement': paiement.date_paiement,
                'reference_mobile_money': paiement.reference_mobile_money,
                'souscription': paiement.souscription_pass.numero_souscription if paiement.souscription_pass else None
            })
        
        # Statistiques paiements
        total_paye = paiements.filter(statut='succes').aggregate(
            total=Sum('montant_net')
        )['total'] or 0
        
        return Response({
            'success': True,
            'data': {
                'client': f"{client.prenom} {client.nom}",
                'statistiques': {
                    'total_paiements': paiements.count(),
                    'total_paye': total_paye,
                    'paiements_reussis': paiements.filter(statut='succes').count(),
                    'paiements_en_cours': paiements.filter(statut='en_cours').count()
                },
                'paiements_par_type': paiements_par_type,
                'historique_complet': [{
                    'numero_transaction': p.numero_transaction,
                    'montant': p.montant,
                    'operateur': p.operateur,
                    'statut': p.statut,
                    'type': p.type_paiement,
                    'date': p.date_paiement
                } for p in paiements[:20]]  # 20 derniers
            }
        }, status=status.HTTP_200_OK)
        
    except NumeroPolice.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Police introuvable'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def agent_stats(request, agent_id):
    """
    Statistiques détaillées d'un agent
    
    GET /api/v1/agents/{id}/stats/
    """
    try:
        agent = get_object_or_404(Agent, id=agent_id)
        
        # Importer ici pour éviter les imports circulaires
        from apps.pass_clients.models import SouscriptionPass
        from apps.pass_payments.models import PaiementPass
        
        # Statistiques souscriptions
        souscriptions = SouscriptionPass.objects.filter(agent=agent)
        souscriptions_actives = souscriptions.filter(statut='activee')
        
        # Statistiques paiements
        paiements_reussis = PaiementPass.objects.filter(
            souscription_pass__agent=agent,
            statut='succes'
        )
        
        # Calculs
        stats = {
            'nombre_souscriptions': souscriptions.count(),
            'souscriptions_actives': souscriptions_actives.count(),
            'chiffre_affaires': paiements_reussis.aggregate(
                total=Sum('montant')
            )['total'] or 0,
            'commissions_dues': 0,  # À calculer selon la logique métier
            'souscriptions_ce_mois': souscriptions.filter(
                date_souscription__month=timezone.now().month,
                date_souscription__year=timezone.now().year
            ).count(),
        }
        
        # Calculer commissions dues
        stats['commissions_dues'] = (
            stats['chiffre_affaires'] * agent.taux_commission / 100
        ) - agent.solde_commissions
        
        # Sérialiser agent avec stats
        serializer = AgentStatsSerializer(agent)
        data = serializer.data
        data.update(stats)
        
        return Response({
            'success': True,
            'data': data
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': 'Erreur lors de la récupération des statistiques',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def agents_dashboard(request):
    """
    Dashboard global des agents avec statistiques
    
    GET /api/v1/agents/dashboard/
    """
    try:
        from apps.pass_clients.models import SouscriptionPass
        from apps.pass_payments.models import PaiementPass
        from django.utils import timezone
        
        # Statistiques globales
        total_agents = Agent.objects.filter(statut='actif').count()
        total_souscriptions = SouscriptionPass.objects.count()
        
        # Top agents ce mois
        current_month = timezone.now().replace(day=1)
        top_agents = Agent.objects.filter(
            statut='actif'
        ).annotate(
            souscriptions_ce_mois=Count(
                'souscriptions',
                filter=Q(souscriptions__date_souscription__gte=current_month)
            )
        ).order_by('-souscriptions_ce_mois')[:5]
        
        # Sérialiser top agents
        top_agents_data = []
        for agent in top_agents:
            agent_data = AgentListSerializer(agent).data
            agent_data['souscriptions_ce_mois'] = agent.souscriptions_ce_mois
            top_agents_data.append(agent_data)
        
        return Response({
            'success': True,
            'data': {
                'statistiques_globales': {
                    'total_agents_actifs': total_agents,
                    'total_souscriptions': total_souscriptions,
                    'moyenne_souscriptions_par_agent': (
                        total_souscriptions / total_agents if total_agents > 0 else 0
                    )
                },
                'top_agents_ce_mois': top_agents_data,
                'repartition_par_agence': list(
                    Agent.objects.filter(statut='actif')
                    .values('agence')
                    .annotate(nombre_agents=Count('id'))
                    .order_by('-nombre_agents')
                )
            }
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': 'Erreur lors de la récupération du dashboard',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_agent_status(request, agent_id):
    """
    Active/désactive un agent
    
    POST /api/v1/agents/{id}/toggle-status/
    """
    try:
        agent = get_object_or_404(Agent, id=agent_id)
        
        # Basculer le statut
        agent.statut = 'inactif' if agent.statut == 'actif' else 'actif'
        agent.save()
        
        return Response({
            'success': True,
            'message': f'Agent {agent.nom_complet} est maintenant {agent.statut}',
            'data': {
                'agent_id': agent.id,
                'nom_complet': agent.nom_complet,
                'nouveau_statut': agent.statut
            }
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': 'Erreur lors du changement de statut',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def agent_login(request):
    """
    Authentification agent pour chatbot
    
    POST /api/v1/auth/agent/login/
    {
        "telephone": "+242061234567",
        "matricule": "AG001"
    }
    """
    try:
        serializer = AgentLoginSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                'success': False,
                'error': 'Données invalides',
                'details': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        agent = serializer.validated_data['agent']
        
        # Créer ou récupérer un utilisateur Django pour l'agent
        username = f"nsia_agent_{agent.matricule.lower()}"
        
        try:
            user = User.objects.get(username=username)
            # Mettre à jour les infos si nécessaire
            user.first_name = agent.prenom
            user.last_name = agent.nom
            user.email = f"{username}@nsia-agent.local"
            user.save()
        except User.DoesNotExist:
            user = User.objects.create_user(
                username=username,
                email=f"{username}@nsia-agent.local",
                first_name=agent.prenom,
                last_name=agent.nom,
            )
        
        # Génération token JWT avec RefreshToken (session courte pour borne)
        refresh = RefreshToken.for_user(user)
        refresh.set_exp(lifetime=timedelta(hours=24))  # Token valide 24h
        
        # Ajout métadonnées agent dans le token
        refresh['user_type'] = 'agent'  # Différencier de 'client'
        refresh['agent_id'] = agent.id
        refresh['matricule'] = agent.matricule
        refresh['nom_complet'] = agent.nom_complet
        refresh['agence'] = agent.agence
        refresh['telephone'] = agent.telephone
        refresh['poste'] = agent.poste
        
        # Token d'accès
        access_token = refresh.access_token
        access_token.set_exp(lifetime=timedelta(minutes=30))  # 30 min pour l'access
        
        # Statistiques agent rapides
        from apps.pass_clients.models import SouscriptionPass
        stats = {
            'total_souscriptions': SouscriptionPass.objects.filter(agent=agent).count(),
            'souscriptions_actives': SouscriptionPass.objects.filter(
                agent=agent, 
                statut='activee'
            ).count(),
            'souscriptions_ce_mois': SouscriptionPass.objects.filter(
                agent=agent,
                date_souscription__month=datetime.now().month,
                date_souscription__year=datetime.now().year
            ).count()
        }
        
        return Response({
            'success': True,
            'message': f'Connexion réussie. Bienvenue {agent.nom_complet}',
            'data': {
                'tokens': {
                    'access': str(access_token),
                    'refresh': str(refresh)
                },
                'agent': {
                    'id': agent.id,
                    'nom_complet': agent.nom_complet,
                    'matricule': agent.matricule,
                    'agence': agent.agence,
                    'telephone': agent.telephone,
                    'poste': agent.poste,
                    'taux_commission': float(agent.taux_commission)
                },
                'statistiques': stats,
                'session': {
                    'expires_in': 86400,  # 24h en secondes
                    'type': 'agent_session'
                }
            }
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': 'Erreur lors de la connexion',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def agent_profile(request):
    """
    Profil de l'agent connecté
    
    GET /api/v1/auth/agent/profile/
    Headers: Authorization: Bearer <token>
    """
    try:
        # Récupérer les infos de l'agent depuis le token JWT
        # Le token contient maintenant les métadonnées via RefreshToken
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        if not auth_header.startswith('Bearer '):
            return Response({
                'success': False,
                'error': 'Token manquant'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Décoder le token pour récupérer les métadonnées
        from rest_framework_simplejwt.tokens import UntypedToken
        from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
        
        token = auth_header.replace('Bearer ', '')
        
        try:
            # Vérifier et décoder le token
            validated_token = UntypedToken(token)
            
            # Vérifier que c'est bien un agent
            if validated_token.get('user_type') != 'agent':
                return Response({
                    'success': False,
                    'error': 'Token non autorisé pour les agents'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # Récupérer l'agent
            agent_id = validated_token.get('agent_id')
            agent = get_object_or_404(Agent, id=agent_id, statut='actif')
            
        except (InvalidToken, TokenError):
            return Response({
                'success': False,
                'error': 'Token invalide ou expiré'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Statistiques détaillées
        from apps.pass_clients.models import SouscriptionPass
        from apps.pass_payments.models import PaiementPass
        
        souscriptions = SouscriptionPass.objects.filter(agent=agent)
        paiements_reussis = PaiementPass.objects.filter(
            souscription_pass__agent=agent,
            statut='succes'
        )
        
        chiffre_affaires = paiements_reussis.aggregate(
            total=Sum('montant')
        )['total'] or 0
        
        stats = {
            'total_souscriptions': souscriptions.count(),
            'souscriptions_actives': souscriptions.filter(statut='activee').count(),
            'chiffre_affaires': float(chiffre_affaires),
            'commissions_dues': float(
                (chiffre_affaires * agent.taux_commission / 100) - agent.solde_commissions
            ),
            'souscriptions_ce_mois': souscriptions.filter(
                date_souscription__month=datetime.now().month,
                date_souscription__year=datetime.now().year
            ).count()
        }
        
        return Response({
            'success': True,
            'data': {
                'agent': AgentSerializer(agent).data,
                'statistiques': stats
            }
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': 'Erreur lors de la récupération du profil',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def agent_logout(request):
    """
    Déconnexion agent - Blacklist du token
    
    POST /api/v1/auth/agent/logout/
    Headers: Authorization: Bearer <access_token>
    Body: {"refresh_token": "..."}
    """
    try:
        refresh_token = request.data.get('refresh_token')
        
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()  # Invalider le refresh token
            except TokenError:
                pass  # Token déjà invalide, pas grave
        
        return Response({
            'success': True,
            'message': 'Déconnexion agent réussie. À bientôt !'
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': 'Erreur lors de la déconnexion',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AgentDetailView(generics.RetrieveAPIView):
    """
    Détail d'un agent avec ses statistiques
    
    GET /api/v1/agents/{id}/
    """
    queryset = Agent.objects.all()
    serializer_class = AgentSerializer
    permission_classes = [IsAuthenticated]
    
    def retrieve(self, request, *args, **kwargs):
        """Détail avec statistiques détaillées"""
        agent = self.get_object()
        
        # Statistiques de l'agent
        from apps.pass_clients.models import SouscriptionPass
        from apps.pass_payments.models import PaiementPass
        
        souscriptions = SouscriptionPass.objects.filter(agent=agent)
        paiements_reussis = PaiementPass.objects.filter(
            souscription_pass__agent=agent,
            statut='succes'
        )
        
        stats = {
            'souscriptions': {
                'total': souscriptions.count(),
                'actives': souscriptions.filter(statut='activee').count(),
                'en_attente': souscriptions.filter(statut='en_attente').count(),
                'suspendues': souscriptions.filter(statut='suspendue').count()
            },
            'chiffre_affaires': {
                'total': float(paiements_reussis.aggregate(
                    total=Sum('montant')
                )['total'] or 0),
                'ce_mois': float(paiements_reussis.filter(
                    date_paiement__month=timezone.now().month,
                    date_paiement__year=timezone.now().year
                ).aggregate(total=Sum('montant'))['total'] or 0)
            },
            'commissions': {
                'solde_actuel': float(agent.solde_commissions),
                'taux': float(agent.taux_commission)
            }
        }
        
        serializer = self.get_serializer(agent)
        return Response({
            'agent': serializer.data,
            'statistiques': stats
        })

class AgentCreateView(generics.CreateAPIView):
    """Vue pour créer un nouvel agent"""
    queryset = Agent.objects.all()
    serializer_class = AgentCreateSerializer
    permission_classes = [AllowAny]  # Ajoutez selon vos besoins
    
    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            agent = serializer.save()
            
            return Response({
                'success': True,
                'message': f'Agent créé avec succès. Matricule: {agent.matricule}',
                'data': {
                    'id': agent.id,
                    'nom_complet': agent.nom_complet,
                    'matricule': agent.matricule,
                    'telephone': agent.telephone,
                    'agence': agent.agence,
                    'statut': agent.statut
                }
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': 'Erreur lors de la création de l\'agent',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AgentUpdateView(generics.UpdateAPIView):
    """Vue pour modifier un agent existant"""
    queryset = Agent.objects.all()
    serializer_class = AgentUpdateSerializer
    # permission_classes = [IsAuthenticated]
    
    def update(self, request, *args, **kwargs):
        try:
            partial = kwargs.pop('partial', False)
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            
            agent = serializer.save()
            
            return Response({
                'success': True,
                'message': 'Agent modifié avec succès',
                'data': {
                    'id': agent.id,
                    'nom_complet': agent.nom_complet,
                    'matricule': agent.matricule,  # Reste inchangé
                    'telephone': agent.telephone,
                    'agence': agent.agence
                }
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': 'Erreur lors de la modification',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AgentListView(generics.ListAPIView):
    """
    Liste des agents avec filtres avancés
    
    GET /api/v1/agents/
    Paramètres:
    - ?search=john (recherche nom/prenom/matricule/telephone)
    - ?agence=Brazzaville Centre
    - ?statut=actif
    - ?poste=Agent Commercial
    - ?ordering=nom,-date_embauche
    - ?page=1&page_size=20
    """
    queryset = Agent.objects.all()
    serializer_class = AgentSerializer
    permission_classes = [IsAuthenticated]
    
    # Filtres et recherche
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['agence', 'statut', 'poste']
    search_fields = ['nom', 'prenom', 'matricule', 'telephone', 'email']
    ordering_fields = ['nom', 'prenom', 'date_embauche', 'matricule', 'agence']
    ordering = ['nom', 'prenom']  # Tri par défaut
    
    def get_queryset(self):
        """Queryset optimisé avec annotations statistiques"""
        queryset = Agent.objects.select_related().annotate(
            # Compter les souscriptions liées
            total_souscriptions=Count('souscriptions_creees'),
            souscriptions_actives=Count(
                'souscriptions_creees',
                filter=Q(souscriptions_creees__statut='activee')
            ),
            # Calculer le CA généré
            chiffre_affaires=Sum(
                'souscriptions_creees__montant_souscription',
                filter=Q(souscriptions_creees__statut='activee')
            )
        )
        
        # Filtres personnalisés
        agence = self.request.query_params.get('agence')
        if agence:
            queryset = queryset.filter(agence__icontains=agence)
            
        statut = self.request.query_params.get('statut')
        if statut:
            queryset = queryset.filter(statut=statut)
            
        # Filtre par performance (agents avec souscriptions)
        avec_souscriptions = self.request.query_params.get('avec_souscriptions')
        if avec_souscriptions == 'true':
            queryset = queryset.filter(total_souscriptions__gt=0)
            
        return queryset
    
    def list(self, request, *args, **kwargs):
        """Response enrichie avec statistiques globales"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            
            # Statistiques globales
            stats_globales = {
                'total_agents': Agent.objects.count(),
                'agents_actifs': Agent.objects.filter(statut='actif').count(),
                'agents_inactifs': Agent.objects.filter(statut='inactif').count(),
                'agences': list(Agent.objects.values_list('agence', flat=True).distinct()),
                'postes': list(Agent.objects.values_list('poste', flat=True).distinct())
            }
            
            # Response paginée avec stats
            response = self.get_paginated_response(serializer.data)
            response.data['statistiques_globales'] = stats_globales
            return response
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'results': serializer.data,
            'count': queryset.count()
        })

class AgentDeleteView(generics.DestroyAPIView):
    """
    Supprimer un agent (avec vérifications de sécurité)
    
    DELETE /api/v1/agents/{id}/delete/
    """
    queryset = Agent.objects.all()
    permission_classes = [IsAuthenticated]
    
    def destroy(self, request, *args, **kwargs):
        try:
            agent = self.get_object()
            
            # ✅ Vérifications avant suppression
            from apps.pass_clients.models import SouscriptionPass
            
            # 1. Vérifier s'il a des souscriptions liées
            souscriptions_count = SouscriptionPass.objects.filter(agent=agent).count()
            
            if souscriptions_count > 0:
                return Response({
                    'success': False,
                    'error': 'Impossible de supprimer cet agent',
                    'details': f'L\'agent a {souscriptions_count} souscriptions liées. Désactivez-le plutôt.',
                    'suggestion': {
                        'action': 'desactiver',
                        'endpoint': f'/api/v1/agents/{agent.id}/toggle-status/',
                        'souscriptions_liees': souscriptions_count
                    }
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 2. Vérifier les paiements en cours
            from apps.pass_payments.models import PaiementPass
            paiements_en_cours = PaiementPass.objects.filter(
                souscription_pass__agent=agent,
                statut__in=['en_cours', 'pending']
            ).count()
            
            if paiements_en_cours > 0:
                return Response({
                    'success': False,
                    'error': 'Impossible de supprimer cet agent',
                    'details': f'L\'agent a {paiements_en_cours} paiements en cours de traitement.',
                    'paiements_en_cours': paiements_en_cours
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 3. Vérifier le solde de commissions
            if agent.solde_commissions > 0:
                return Response({
                    'success': False,
                    'error': 'Impossible de supprimer cet agent',
                    'details': f'L\'agent a un solde de commissions de {agent.solde_commissions} FCFA non soldé.',
                    'solde_commissions': float(agent.solde_commissions)
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # ✅ Suppression autorisée
            agent_info = {
                'id': agent.id,
                'nom_complet': agent.nom_complet,
                'matricule': agent.matricule
            }
            
            agent.delete()
            
            return Response({
                'success': True,
                'message': f'Agent {agent_info["nom_complet"]} ({agent_info["matricule"]}) supprimé avec succès',
                'agent_supprime': agent_info
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': 'Erreur lors de la suppression',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
