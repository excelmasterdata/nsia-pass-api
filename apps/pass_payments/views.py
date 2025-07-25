from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db import transaction

from apps.airtel_integration.models import TransactionAirtel
from apps.pass_clients.services import SouscriptionPassService
from apps.pass_payments.services import PaymentServiceFactory
from .models import PaiementPass
from apps.pass_clients.models import ClientPass, SouscriptionPass
from apps.pass_products.models import ProduitPass, BeneficiairePass
from apps.borne_auth.models import NumeroPolice
from apps.mtn_integration.services import MTNMobileMoneyService
from apps.mtn_integration.models import TransactionMTN
import uuid
from datetime import datetime
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods
import json
import logging
from django.http import JsonResponse
from datetime import datetime

# Logger
logger = logging.getLogger(__name__)

# ===== NOUVEAUX ENDPOINTS FLEXIBLES =====

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def initier_paiement_flexible(request):
    """
    🚀 NOUVEAU : Initie un paiement avec choix d'opérateur
    
    POST /api/v1/paiements/initier/
    {
        "police": "CG-2024-ACC-001",
        "montant": 1250,
        "numero_payeur": "+242061234567",
        "operateur": "mtn_money",  // "mtn_money" | "airtel_money"
        "type_paiement": "cotisation"
    }
    """
    try:
        # Récupération des données
        police = request.data.get('police')
        montant = int(request.data.get('montant', 0))
        numero_payeur = request.data.get('numero_payeur')
        operateur = request.data.get('operateur')
        type_paiement = request.data.get('type_paiement', 'cotisation')
        
        # Validations
        if not all([police, montant > 0, numero_payeur, operateur]):
            return Response({
                'success': False,
                'error': 'Données manquantes: police, montant, numero_payeur, operateur requis'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Vérifier opérateur supporté
        if operateur not in PaymentServiceFactory.get_supported_operators():
            return Response({
                'success': False,
                'error': f'Opérateur non supporté. Disponibles: {PaymentServiceFactory.get_supported_operators()}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Récupérer la souscription
        try:
            numero_police_obj = NumeroPolice.objects.get(numero_police=police)
            souscription = numero_police_obj.souscription_pass
        except NumeroPolice.DoesNotExist:
            return Response({
                'success': False,
                'error': f'Police {police} non trouvée'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Créer l'enregistrement de paiement
        paiement = PaiementPass.objects.create(
            souscription_pass=souscription,
            client=souscription.client,
            montant=montant,
            operateur=operateur,
            numero_payeur=numero_payeur,
            type_paiement=type_paiement,
            statut='en_cours'
        )
        
        # Refresh pour récupérer le numero_transaction auto-généré
        paiement.refresh_from_db()
        
        # Obtenir le service approprié
        payment_service = PaymentServiceFactory.get_service(operateur)
        
        # Initier le paiement selon l'opérateur
        if operateur == 'mtn_money':
            # Créer transaction MTN
            transaction_mtn = TransactionMTN.objects.create(
                external_id=paiement.numero_transaction,
                paiement_pass=paiement,
                type_transaction='request_to_pay',
                montant=montant,
                payer_msisdn=numero_payeur,
                statut='initiated',
                request_payload=request.data
            )
            
            result = payment_service.request_to_pay(
                amount=montant,
                phone_number=numero_payeur,
                external_id=paiement.numero_transaction,
                payer_message=f"Paiement NSIA PASS - {type_paiement}"
            )
            
            if result.get('success'):
                # Mettre à jour la transaction MTN
                transaction_mtn.financial_transaction_id = result['reference_id']
                transaction_mtn.statut = 'pending'
                transaction_mtn.response_payload = result
                transaction_mtn.save()
                
                return Response({
                    'success': True,
                    'message': 'Demande de paiement MTN envoyée sur votre téléphone',
                    'data': {
                        'numero_transaction': paiement.numero_transaction,
                        'reference_mtn': result['reference_id'],
                        'montant': montant,
                        'operateur': operateur,
                        'statut': 'en_cours',
                        'instructions': 'Vérifiez votre téléphone MTN et confirmez le paiement'
                    }
                })
            else:
                # Échec du paiement
                paiement.statut = 'echec'
                paiement.motif_echec = result.get('error', 'Erreur MTN')
                paiement.save()
                
                return Response({
                    'success': False,
                    'error': f'Échec paiement {operateur}',
                    'details': result.get('error')
                }, status=status.HTTP_400_BAD_REQUEST)
        
        elif operateur == 'airtel_money':
            result = payment_service.debit_request(
                amount=montant,
                phone_number=numero_payeur,
                external_id=paiement.numero_transaction
            )
            
            if result.get('success'):
                # Traitement spécifique Airtel
                return Response({
                    'success': True,
                    'message': 'Demande de paiement Airtel envoyée',
                    'data': {
                        'numero_transaction': paiement.numero_transaction,
                        'reference_airtel': result.get('transaction_id'),
                        'montant': montant,
                        'operateur': operateur,
                        'statut': 'en_cours',
                        'instructions': 'Confirmez le paiement sur votre téléphone Airtel'
                    }
                })
                
    except Exception as e:
        logger.error(f"Erreur paiement flexible: {e}")
        return Response({
            'success': False,
            'error': 'Erreur lors de l\'initiation du paiement',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def operateurs_supportes(request):
    """
    🚀 NOUVEAU : Liste des opérateurs de paiement supportés
    
    GET /api/v1/paiements/operateurs/
    """
    operateurs = [
        {
            'code': 'mtn_money',
            'nom': 'MTN Mobile Money',
            'prefixes': ['061', '062', '063', '064', '065'],
            'logo': '/static/images/mtn_logo.png',
            'disponible': True
        },
        {
            'code': 'airtel_money',
            'nom': 'Airtel Money',
            'prefixes': ['055', '056', '057', '058', '059'],
            'logo': '/static/images/airtel_logo.png',
            'disponible': True  # Changer à True quand prêt
        }
    ]
    
    return Response({
        'success': True,
        'data': {
            'operateurs': operateurs,
            'total': len(operateurs),
            'disponibles': [op for op in operateurs if op['disponible']]
        }
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def detecter_operateur(request):
    """
    🚀 NOUVEAU : Détecte automatiquement l'opérateur basé sur le numéro
    
    POST /api/v1/paiements/detecter-operateur/
    {
        "numero_telephone": "+242061234567"
    }
    """
    numero = request.data.get('numero_telephone')
    
    if not numero:
        return Response({
            'success': False,
            'error': 'Numéro de téléphone requis'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    operateur_detecte = PaymentServiceFactory.detect_operator_from_phone(numero)
    
    if operateur_detecte:
        # Vérifier si l'opérateur est disponible
        operateurs_disponibles = PaymentServiceFactory.get_supported_operators()
        disponible = operateur_detecte in operateurs_disponibles
        
        return Response({
            'success': True,
            'data': {
                'operateur_detecte': operateur_detecte,
                'numero_telephone': numero,
                'disponible': disponible,
                'recommandation': f'Utilisez {operateur_detecte} pour ce numéro' if disponible else f'{operateur_detecte} bientôt disponible'
            }
        })
    else:
        return Response({
            'success': True,
            'data': {
                'operateur_detecte': None,
                'numero_telephone': numero,
                'disponible': False,
                'recommandation': 'Veuillez choisir manuellement votre opérateur'
            }
        })

# ===== ENDPOINTS EXISTANTS (avec rétrocompatibilité) =====

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def initier_paiement_borne(request):
    """
    ⚠️ ANCIEN : Initie un paiement MTN depuis la borne interactive (rétrocompatibilité)
    
    POST /api/v1/paiements/mtn/initier/
    """
    # Ajouter l'opérateur MTN par défaut et rediriger vers la nouvelle fonction
    request.data['operateur'] = 'mtn_money'
    return initier_paiement_flexible(request)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def verifier_statut_paiement_borne(request, numero_transaction):
    """
    Vérifie le statut d'un paiement depuis la borne (compatible tous opérateurs)
    
    GET /api/v1/paiements/statut/{numero_transaction}/
    """
    try:
        paiement = get_object_or_404(PaiementPass, numero_transaction=numero_transaction)
        
        # Logique selon l'opérateur
        if paiement.operateur == 'mtn_money':
            transaction_mtn = get_object_or_404(TransactionMTN, external_id=numero_transaction)
            
            # Vérifier le statut auprès de MTN
            mtn_service = MTNMobileMoneyService()
            result = mtn_service.check_payment_status(transaction_mtn.financial_transaction_id)
            
            if result['success']:
                mtn_status = result['status']
                
                # Mapper le statut MTN
                if mtn_status == 'SUCCESSFUL':
                    paiement.statut = 'succes'
                    paiement.code_confirmation = result.get('financial_transaction_id', '')
                    paiement.date_confirmation = datetime.now()
                    message = 'Paiement MTN effectué avec succès'
                        
                elif mtn_status == 'FAILED':
                    paiement.statut = 'echec'
                    paiement.motif_echec = result.get('reason', 'Paiement MTN rejeté')
                    message = 'Paiement MTN échoué'
                    
                else:  # PENDING
                    paiement.statut = 'en_cours'
                    message = 'Paiement MTN en cours de traitement'
                
                paiement.save()
                
                return Response({
                    'success': True,
                    'data': {
                        'numero_transaction': numero_transaction,
                        'statut': paiement.statut,
                        'operateur': paiement.operateur,
                        'montant': paiement.montant,
                        'date_paiement': paiement.date_paiement,
                        'statut_operateur': mtn_status,
                        'message': message
                    }
                })
        
        elif paiement.operateur == 'airtel_money':
            # TODO: Ajouter la vérification Airtel quand prêt
            return Response({
                'success': True,
                'data': {
                    'numero_transaction': numero_transaction,
                    'statut': paiement.statut,
                    'operateur': paiement.operateur,
                    'montant': paiement.montant,
                    'message': 'Vérification Airtel bientôt disponible'
                }
            })
        
        return Response({
            'success': False,
            'error': 'Opérateur non reconnu'
        }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        return Response({
            'success': False,
            'error': 'Erreur technique',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def nouvelle_souscription_avec_paiement(request):
    """
    Crée une nouvelle souscription PASS avec paiement flexible
    
    POST /api/v1/paiements/nouvelle-souscription/
    {
        "produit_pass_id": 1,
        "operateur": "mtn_money",
        "client": {
            "nom": "KONGO",
            "prenom": "Jean Baptiste",
            "telephone": "+242061234567",
            "adresse": "Poto-Poto, Brazzaville"
        },
        "beneficiaires": [...],
        "montant": 5000
    }
    """
    try:
        with transaction.atomic():
            # 1. Extraire et valider les données
            produit_pass_id = request.data.get('produit_pass_id')
            operateur = request.data.get('operateur', 'mtn_money')
            client_data = request.data.get('client', {})
            beneficiaires_data = request.data.get('beneficiaires', [])
            montant = int(request.data.get('montant', 0))
            
            # Validation de base
            if not all([produit_pass_id, client_data.get('telephone'), montant > 0]):
                return Response({
                    'success': False,
                    'error': 'Données manquantes pour la souscription'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Vérifier opérateur supporté
            if operateur not in PaymentServiceFactory.get_supported_operators():
                return Response({
                    'success': False,
                    'error': f'Opérateur {operateur} non supporté'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 2. Récupérer le produit PASS
            produit_pass = get_object_or_404(ProduitPass, id=produit_pass_id)
            
            # 3. Auto-détection d'opérateur si nécessaire
            telephone = client_data['telephone']
            if not operateur or operateur == 'auto':
                operateur_detecte = PaymentServiceFactory.detect_operator_from_phone(telephone)
                if operateur_detecte and operateur_detecte in PaymentServiceFactory.get_supported_operators():
                    operateur = operateur_detecte
                else:
                    operateur = 'mtn_money'  # Défaut
            
            # 4. ✅ UTILISER LE SERVICE pour créer la souscription
            donnees_souscription = {
                'code_pass': produit_pass.code_pass,
                'montant_souscription': montant,
                'client': {
                    'telephone': telephone,
                    'nom': client_data.get('nom', ''),
                    'prenom': client_data.get('prenom', ''),
                    'adresse': client_data.get('adresse', ''),
                    'operateur_mobile': operateur.replace('_money', '')  # mtn ou airtel
                },
                'beneficiaires': beneficiaires_data,
                'periodicite': request.data.get('periodicite', 'mensuelle'),
                'commentaires': f'Souscription via {operateur}'
            }
            
            # Créer la souscription via le service
            resultat_souscription = SouscriptionPassService.creer_souscription_pass(
                donnees_souscription
            )
            
            souscription = resultat_souscription['souscription']
            client = resultat_souscription['client']
            
            # 5. Créer le paiement initial
            paiement = PaiementPass.objects.create(
                souscription_pass=souscription,
                client=client,
                montant=montant,
                operateur=operateur,
                numero_payeur=telephone,
                type_paiement='souscription_initiale',
                statut='en_cours'
            )
            
            paiement.refresh_from_db()
            
            # 6. Initier le paiement selon l'opérateur
            payment_service = PaymentServiceFactory.get_service(operateur)
            
            if operateur == 'mtn_money':
                result = payment_service.request_to_pay(
                    amount=montant,
                    phone_number=telephone,
                    external_id=paiement.numero_transaction,
                    payer_message=f"Souscription NSIA PASS {produit_pass.nom_pass}"
                )
                
                if result['success']:
                    # Créer transaction MTN
                    TransactionMTN.objects.create(
                        external_id=paiement.numero_transaction,
                        paiement_pass=paiement,
                        type_transaction='request_to_pay',
                        montant=montant,
                        payer_msisdn=telephone.replace('+', '').replace(' ', ''),
                        financial_transaction_id=result['reference_id'],
                        statut='pending',
                        request_payload=request.data,
                        response_payload=result
                    )
                    
                    return Response({
                        'success': True,
                        'message': f'Souscription créée. Confirmez le paiement MTN sur votre téléphone.',
                        'data': {
                            'souscription_id': souscription.id,
                            'numero_souscription': souscription.numero_souscription,
                            'numero_transaction': paiement.numero_transaction,
                            'reference_mtn': result['reference_id'],
                            'montant': montant,
                            'operateur': operateur,
                            'produit': produit_pass.nom_pass,
                            'client_cree': resultat_souscription['client_created'],
                            'beneficiaires_count': len(resultat_souscription['beneficiaires']),
                            'instructions': 'Vérifiez votre téléphone MTN Mobile Money et confirmez le paiement'
                        }
                    })
                else:
                    # Échec du paiement - annuler la souscription
                    souscription.delete()
                    return Response({
                        'success': False,
                        'error': f'Impossible d\'initier le paiement MTN pour cette souscription',
                        'details': result.get('error', 'Erreur technique MTN')
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            elif operateur == 'airtel_money':
                result = payment_service.debit_request(
                    amount=montant,
                    phone_number=telephone,
                    external_id=paiement.numero_transaction
                )
                
                if result.get('success'):
                    airtel_data = result.get('data', {})
                    
                    # Récupérer la référence Airtel
                    reference_airtel = (
                        airtel_data.get('data', {}).get('transaction', {}).get('id') or
                        airtel_data.get('transaction', {}).get('id') or
                        f"AIRTEL-{paiement.numero_transaction}"
                    )
                    
                    # Créer transaction Airtel
                    TransactionAirtel.objects.create(
                        external_id=paiement.numero_transaction,
                        paiement_pass=paiement,
                        type_transaction='debit_request',
                        montant=montant,
                        payer_msisdn=telephone.removeprefix('242'),
                        airtel_transaction_id=reference_airtel,
                        statut='pending',
                        request_payload=request.data,
                        response_payload=result
                    )
                    
                    # Sauvegarder la référence
                    paiement.reference_mobile_money = reference_airtel
                    paiement.save()
                    
                    return Response({
                        'success': True,
                        'message': 'Souscription créée. Confirmez le paiement Airtel sur votre téléphone.',
                        'data': {
                            'souscription_id': souscription.id,
                            'numero_souscription': souscription.numero_souscription,
                            'numero_transaction': paiement.numero_transaction,
                            'reference_airtel': reference_airtel,
                            'montant': montant,
                            'operateur': operateur,
                            'produit': produit_pass.nom_pass,
                            'client_cree': resultat_souscription['client_created'],
                            'beneficiaires_count': len(resultat_souscription['beneficiaires']),
                            'instructions': 'Vérifiez votre téléphone Airtel Money et confirmez le paiement'
                        }
                    })
                else:
                    # Échec du paiement - annuler la souscription
                    souscription.delete()
                    return Response({
                        'success': False,
                        'error': f'Impossible d\'initier le paiement Airtel pour cette souscription',
                        'details': result.get('error', 'Erreur technique Airtel')
                    }, status=status.HTTP_400_BAD_REQUEST)
                
    except ValueError as ve:
        # Erreurs de validation du service
        return Response({
            'success': False,
            'error': 'Erreur de validation',
            'details': str(ve)
        }, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': 'Erreur lors de la création de la souscription',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def historique_paiements_client(request, police):
    """
    Récupère l'historique des paiements d'un client via sa police (tous opérateurs)
    
    GET /api/v1/paiements/historique/{police}/
    """
    try:
        # Récupérer la souscription via la police
        numero_police_obj = get_object_or_404(NumeroPolice, numero_police=police)
        souscription = numero_police_obj.souscription_pass
        
        # Récupérer tous les paiements du client
        paiements = PaiementPass.objects.filter(
            souscription_pass=souscription
        ).order_by('-date_paiement')
        
        # Formater les données
        paiements_data = []
        for paiement in paiements:
            paiements_data.append({
                'numero_transaction': paiement.numero_transaction,
                'montant': int(paiement.montant),
                'operateur': paiement.operateur,
                'type_paiement': paiement.type_paiement,
                'statut': paiement.statut,
                'date_paiement': paiement.date_paiement.isoformat(),
                'date_confirmation': paiement.date_confirmation.isoformat() if paiement.date_confirmation else None,
                'motif_echec': paiement.motif_echec
            })
        
        return Response({
            'success': True,
            'data': {
                'police': police,
                'client': souscription.client.nom_complet,
                'paiements': paiements_data,
                'total_paiements': len(paiements_data),
                'montant_total': sum(p.montant for p in paiements),
                'operateurs_utilises': list(set(p['operateur'] for p in paiements_data))
            }
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': 'Erreur lors de la récupération de l\'historique',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@csrf_exempt
@require_http_methods(["POST"])
def mtn_callback(request):
    """
    Webhook de callback MTN Mobile Money (inchangé)
    
    POST /api/v1/mtn/callback/
    """
    try:
        # Récupérer les données du callback
        callback_data = json.loads(request.body.decode('utf-8'))
        
        # Extraire les informations importantes
        reference_id = callback_data.get('referenceId')
        status = callback_data.get('status')
        external_id = callback_data.get('externalId')
        
        if not all([reference_id, external_id]):
            return JsonResponse({'error': 'Données callback invalides'}, status=400)
        
        # Trouver la transaction correspondante
        try:
            transaction_mtn = TransactionMTN.objects.get(
                financial_transaction_id=reference_id,
                external_id=external_id
            )
            paiement = transaction_mtn.paiement_pass
            
            # Mettre à jour selon le statut
            if status == 'SUCCESSFUL':
                paiement.statut = 'succes'
                paiement.date_confirmation = datetime.now()
                
                # Activer la souscription si nécessaire
                if paiement.type_paiement == 'souscription_initiale':
                    paiement.souscription_pass.statut = 'activee'
                    paiement.souscription_pass.paiement_initial_recu = True
                    paiement.souscription_pass.save()
                    
            elif status == 'FAILED':
                paiement.statut = 'echec'
                paiement.motif_echec = callback_data.get('reason', 'Échec MTN')
                
            # Sauvegarder
            paiement.save()
            
            transaction_mtn.statut = status.lower()
            transaction_mtn.callback_payload = callback_data
            transaction_mtn.save()
            
            # Log du callback
            logger.info(f"Callback MTN traité: {external_id} - {status}")
            
            return JsonResponse({'status': 'success'})
            
        except TransactionMTN.DoesNotExist:
            logger.error(f"Transaction MTN non trouvée: {reference_id}")
            return JsonResponse({'error': 'Transaction non trouvée'}, status=404)
            
    except Exception as e:
        logger.error(f"Erreur callback MTN: {e}")
        return JsonResponse({'error': 'Erreur serveur'}, status=500)
