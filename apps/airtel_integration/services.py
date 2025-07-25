# apps/airtel_integration/services.py - Nouveau fichier

import requests
import json
from django.conf import settings
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

class AirtelMoneyService:
    """Service pour Airtel Money Congo"""
    
    def __init__(self):
        self.base_url = 'https://openapi.airtel.africa'
        self.client_id = settings.AIRTEL_MONEY['CLIENT_ID']
        self.client_secret = settings.AIRTEL_MONEY['CLIENT_SECRET']
        
    def _get_access_token(self):
        """Récupère un token d'accès Airtel"""
        cached_token = cache.get('airtel_access_token')
        if cached_token:
            return cached_token
            
        try:
            url = f"{self.base_url}/auth/oauth2/token"
            
            payload = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "client_credentials"
            }
            
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            
            token_data = response.json()
            access_token = token_data.get('access_token')
            expires_in = token_data.get('expires_in', 3600)
            
            cache.set('airtel_access_token', access_token, expires_in - 600)
            return access_token
            
        except Exception as e:
            logger.error(f"Erreur token Airtel: {e}")
            return None
    
    def debit_request(self, amount, phone_number, external_id):
        """Initie un paiement Airtel Money"""
        try:
            token = self._get_access_token()
            if not token:
                return {'success': False, 'error': 'Token Airtel non disponible'}
                
            url = f"{self.base_url}/merchant/v1/payments/"
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}',
                'X-Country': 'CG',
                'X-Currency': 'XAF'
            }
            
            clean_phone = phone_number.removeprefix('+242')
            
            payload = {
                "reference": "NSIA PASS",
                "subscriber": {
                    "country": "CG",
                    "currency": "XAF",
                    "msisdn": clean_phone
                },
                "transaction": {
                    "amount": str(amount),
                    "country": "CG",
                    "currency": "XAF",
                    "id": external_id
                }
            }
            
            print("\n" + "="*50)
            print("🚀 AIRTEL DEBUG - REQUÊTE")
            print("="*50)
            print(f"URL: {url}")
            print(f"Headers: {headers}")
            print(f"Payload: {payload}")
            print(f"Clean Phone: {clean_phone}")
            
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            
            print("\n" + "="*50)
            print("📊 AIRTEL DEBUG - RÉPONSE")
            print("="*50)
            print(f"Status Code: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            print(f"Raw Response Text: '{response.text}'")
            print(f"Response Length: {len(response.text)} caractères")
            
            # Essayer de parser JSON
            try:
                if response.text.strip():
                    response_json = response.json()
                    print(f"Response JSON: {response_json}")
                    print(f"JSON Type: {type(response_json)}")
                    
                    # Explorer toutes les clés récursivement
                    def explore_json(data, indent=0):
                        spaces = "  " * indent
                        if isinstance(data, dict):
                            print(f"{spaces}📁 Dict avec {len(data)} clés:")
                            for key, value in data.items():
                                print(f"{spaces}  🔑 '{key}' = {repr(value)} (type: {type(value).__name__})")
                                if isinstance(value, (dict, list)) and indent < 3:
                                    explore_json(value, indent + 1)
                        elif isinstance(data, list):
                            print(f"{spaces}📋 List avec {len(data)} éléments:")
                            for i, item in enumerate(data[:3]):  # Max 3 éléments
                                print(f"{spaces}  [{i}] = {repr(item)}")
                                if isinstance(item, (dict, list)) and indent < 3:
                                    explore_json(item, indent + 1)
                    
                    print("\n🔍 EXPLORATION COMPLÈTE:")
                    explore_json(response_json)
                    
                else:
                    print("⚠️ Réponse vide!")
                    response_json = {}
            except Exception as json_error:
                print(f"❌ Erreur parsing JSON: {json_error}")
                response_json = {}
            
            print("="*50)
            print("🏁 FIN DEBUG AIRTEL")
            print("="*50 + "\n")
            
            # Logique de retour
            if response.status_code in [200, 201, 202]:
                return {
                    'success': True,
                    'data': response_json,
                    'raw_response': response.text,
                    'status_code': response.status_code,
                    'message': 'Paiement Airtel initié'
                }
            else:
                return {
                    'success': False,
                    'error': f'Erreur Airtel: {response.status_code}',
                    'details': response.text,
                    'status_code': response.status_code
                }
                
        except Exception as e:
            print(f"💥 EXCEPTION AIRTEL: {e}")
            return {'success': False, 'error': str(e)}


    def check_payment_status(self, transaction_id):
        """Vérifie le statut d'un paiement Airtel Money"""
        try:
            token = self._get_access_token()
            if not token:
                return {'success': False, 'error': 'Token Airtel non disponible'}
            
            url = f"{self.base_url}/standard/v1/payments/{transaction_id}"
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}',
                'X-Country': 'CG',
                'X-Currency': 'XAF'
            }
            
            print(f"🔍 Vérification statut Airtel: {transaction_id}")
            
            response = requests.get(url, headers=headers, timeout=30)
            
            print(f"Status Check Response: {response.status_code}")
            print(f"Response Text: {response.text}")
            
            if response.status_code == 200:
                response_data = response.json()
                
                # ✅ CORRECTION: Mapper correctement les statuts Airtel
                transaction_data = response_data.get('data', {}).get('transaction', {})
                airtel_status = transaction_data.get('status', '').upper()
                message = transaction_data.get('message', '')
                
                print(f"🔍 Statut Airtel brut: '{airtel_status}'")
                print(f"🔍 Message: '{message}'")
                
                # Mapping des statuts Airtel spécifiques
                if airtel_status == 'TS':  # ← TS = Transaction Successful
                    return {
                        'success': True,
                        'status': 'SUCCESSFUL',
                        'transaction_id': transaction_id,
                        'airtel_money_id': transaction_data.get('airtel_money_id'),
                        'message': message,
                        'airtel_response': response_data
                    }
                elif airtel_status in ['TF', 'FAILED', 'REJECTED', 'CANCELLED']:
                    return {
                        'success': True,
                        'status': 'FAILED',
                        'reason': message or 'Paiement Airtel échoué',
                        'airtel_response': response_data
                    }
                elif airtel_status in ['TI', 'PENDING', 'INITIATED']:  # TI = Transaction Initiated
                    return {
                        'success': True,
                        'status': 'PENDING',
                        'message': message,
                        'airtel_response': response_data
                    }
                else:
                    # Statut inconnu - considérer comme pending
                    print(f"⚠️ Statut Airtel inconnu: '{airtel_status}' - considéré comme PENDING")
                    return {
                        'success': True,
                        'status': 'PENDING',
                        'unknown_status': airtel_status,
                        'airtel_response': response_data
                    }
            
            elif response.status_code == 404:
                return {
                    'success': True,
                    'status': 'PENDING',
                    'message': 'Transaction en cours de traitement'
                }
            
            else:
                print(f"❌ Erreur Airtel Status {response.status_code}: {response.text}")
                return {
                    'success': False,
                    'error': f'Erreur API Airtel: {response.status_code}',
                    'details': response.text
                }
                
        except Exception as e:
            print(f"💥 Exception vérification Airtel: {e}")
            return {'success': False, 'error': str(e)}