from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum, Count
from apps.pass_clients.models import ClientPass, SouscriptionPass
from apps.pass_payments.models import PaiementPass
from apps.borne_auth.serializers import BorneAuthenticationSerializer
from apps.borne_auth.models import NumeroPolice

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
            statut__in=['activee', 'en_cours']
        ).count()
        
        # Valeur totale des souscriptions
        valeur_totale = souscriptions.aggregate(
            total=Sum('montant_souscription')
        )['total'] or 0
        
        # Contrats (vues) basés sur souscriptions avec police
        contrats = []
        polices_client = NumeroPolice.objects.filter(
            souscription_pass__client=client
        ).select_related('souscription_pass__produit_pass')
        
        for p in polices_client:
            contrats.append({
                'police': p.numero_police,
                'produit': p.souscription_pass.produit_pass.nom_pass,
                'montant': p.souscription_pass.montant_souscription,
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
