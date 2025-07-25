import requests
import uuid
import json
from datetime import datetime, timedelta
from django.conf import settings
from django.core.cache import cache
import logging
import base64

logger = logging.getLogger(__name__)

class MTNMobileMoneyService:
    """Service pour l'intégration MTN Mobile Money Congo"""
    
    def __init__(self):
        self.config = settings.MTN_MOBILE_MONEY
        self.base_url = self.config['BASE_URL']
        self.subscription_key = self.config['COLLECTION_SUBSCRIPTION_KEY']
        self.api_key = self.config['COLLECTION_API_KEY']
        self.user_id = self.config['COLLECTION_USER_ID']
        
    def _get_headers(self, include_auth=True):
        """Génère les headers pour les requêtes MTN"""
        headers = {
            'Content-Type': 'application/json',
            'X-Reference-Id': str(uuid.uuid4()),
            'X-Target-Environment': self.config['ENVIRONMENT'],
            'Ocp-Apim-Subscription-Key': self.subscription_key,
            'X-Callback-Url': 'https://165.232.40.247/ussd/callback_handler/',
            'Cache-Control': 'no-cache'
            
        }
        
        if include_auth:
            token = self._get_access_token()
            if token:
                headers['Authorization'] = f'Bearer {token}'
        
        return headers
    
    def _get_access_token(self):
        """Récupère ou génère un token d'accès MTN"""
            
        # Générer un nouveau token
        try:
            url = f"{self.base_url}/collection/token/"
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': 'Basic NTMwODdiMDctODcyOS00MGM1LWFhNDYtODAzNjcyMmFlZTNkOjBiZjI3MzJmMmQwNTQyMDliNDUzZTBjNjIwNDlhMmU4',
                'Ocp-Apim-Subscription-Key': self.subscription_key,
                'Content-Length': '0'

            }
            
            response = requests.post(url, headers=headers)
            response.raise_for_status()
            
            token_data = response.json()
            access_token = token_data.get('access_token')
            

            return access_token
            
        except Exception as e:
            logger.error(f"Erreur génération token MTN: {e}")
            return None
    
    def request_to_pay(self, amount, phone_number, external_id, payer_message="Paiement NSIA PASS"):
        """
        Initie une demande de paiement MTN Mobile Money
        
        Args:
            amount (int): Montant en XAF
            phone_number (str): Numéro de téléphone au format +242XXXXXXXX
            external_id (str): ID unique de la transaction
            payer_message (str): Message pour le payeur
            
        Returns:
            dict: Résultat de la demande de paiement
        """
        try:
            # Nettoyer le numéro de téléphone (format MTN attendu)
            clean_phone = phone_number.replace('+', '').replace(' ', '')
            if not clean_phone.startswith('242'):
                clean_phone = f"242{clean_phone}"
            
            url = f"{self.base_url}/collection/v1_0/requesttopay"
            reference_id = str(uuid.uuid4())
            
            payload = {
                "amount": str(amount),
                "currency": "XAF",
                "externalId": str(uuid.uuid4()),
                "payer": {
                    "partyIdType": "MSISDN",
                    "partyId": clean_phone
                },
                "payerMessage": payer_message,
                "payeeNote": f"NSIA PASS - Transaction {external_id}"
            }
            
            headers = self._get_headers()
            headers['X-Reference-Id'] = reference_id
            
            response = requests.post(
                url, 
                headers=headers, 
                data=json.dumps(payload)
            )
            
            
            # Log de la requête
            logger.info(f"MTN Request to Pay: {reference_id} - {response.status_code}")
            
            if response.status_code == 202:  # Accepted
                return {
                    'success': True,
                    'reference_id': reference_id,
                    'external_id': external_id,
                    'status': 'PENDING',
                    'message': 'Demande de paiement initiée avec succès'
                }
            else:
                logger.error(f"Erreur MTN Request to Pay: {response.status_code} - {response.text}")
                return {
                    'success': False,
                    'error': 'Erreur lors de l\'initiation du paiement',
                    'details': response.text
                }
                
        except Exception as e:
            logger.error(f"Exception MTN Request to Pay: {e}")
            return {
                'success': False,
                'error': 'Erreur technique lors du paiement',
                'details': str(e)
            }
    
    def check_payment_status(self, reference_id):
        """
        Vérifie le statut d'un paiement MTN
        
        Args:
            reference_id (str): Reference ID de la transaction
            
        Returns:
            dict: Statut du paiement
        """
        try:
            url = f"{self.base_url}/collection/v1_0/requesttopay/{reference_id}"
            headers = self._get_headers()
            
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                payment_data = response.json()
                return {
                    'success': True,
                    'status': payment_data.get('status', 'UNKNOWN'),
                    'amount': payment_data.get('amount'),
                    'currency': payment_data.get('currency'),
                    'financial_transaction_id': payment_data.get('financialTransactionId'),
                    'external_id': payment_data.get('externalId'),
                    'reason': payment_data.get('reason')
                }
            else:
                return {
                    'success': False,
                    'error': 'Impossible de vérifier le statut',
                    'details': response.text
                }
                
        except Exception as e:
            logger.error(f"Erreur vérification statut MTN: {e}")
            return {
                'success': False,
                'error': 'Erreur technique',
                'details': str(e)
            }
    
    def get_account_balance(self):
        """Récupère le solde du compte MTN Collection"""
        try:
            url = f"{self.base_url}/collection/v1_0/account/balance"
            headers = self._get_headers()
            
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                balance_data = response.json()
                return {
                    'success': True,
                    'available_balance': balance_data.get('availableBalance'),
                    'currency': balance_data.get('currency')
                }
            else:
                return {
                    'success': False,
                    'error': 'Impossible de récupérer le solde'
                }
                
        except Exception as e:
            logger.error(f"Erreur récupération solde MTN: {e}")
            return {
                'success': False,
                'error': 'Erreur technique'
            }
