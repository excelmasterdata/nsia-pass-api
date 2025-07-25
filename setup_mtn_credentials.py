# ===============================================
# SCRIPT MTN MOBILE MONEY - CRÉATION USER ID ET API KEY
# Génération automatique des credentials MTN
# ===============================================

import requests
import uuid
import base64
import json
from decouple import config

# ===============================================
# 1. CONFIGURATION INITIALE
# ===============================================

class MTNCredentialsSetup:
    """Script pour créer automatiquement les credentials MTN"""
    
    def __init__(self, subscription_key, environment='sandbox'):
        self.subscription_key = subscription_key  # Votre clé primaire ou secondaire
        self.environment = environment
        
        # URLs selon l'environnement
        if environment == 'sandbox':
            self.base_url = 'https://sandbox.momodeveloper.mtn.com'
        else:
            self.base_url = 'https://ericssonbasicapi2.azure-api.net'
    
    def create_user_id(self, callback_host="your-domain.com"):
        """
        Étape 1: Créer un User ID
        
        Args:
            callback_host (str): Votre domaine pour les callbacks
            
        Returns:
            dict: Résultat avec user_id créé
        """
        print("🔧 Création du User ID MTN...")
        
        try:
            # Générer un UUID unique pour le User ID
            user_id = str(uuid.uuid4())
            
            url = f"{self.base_url}/v1_0/apiuser"
            
            headers = {
                'X-Reference-Id': user_id,
                'Content-Type': 'application/json',
                'Ocp-Apim-Subscription-Key': self.subscription_key
            }
            
            payload = {
                "providerCallbackHost": callback_host
            }
            
            print(f"📋 User ID généré: {user_id}")
            print(f"🌐 Callback Host: {callback_host}")
            print(f"🔗 URL: {url}")
            
            response = requests.post(
                url, 
                headers=headers, 
                data=json.dumps(payload),
                timeout=30
            )
            
            print(f"📊 Status Code: {response.status_code}")
            
            if response.status_code == 201:
                print("✅ User ID créé avec succès!")
                return {
                    'success': True,
                    'user_id': user_id,
                    'message': 'User ID créé avec succès'
                }
            else:
                print(f"❌ Erreur création User ID: {response.status_code}")
                print(f"📄 Réponse: {response.text}")
                return {
                    'success': False,
                    'error': f"Erreur {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            print(f"❌ Exception lors de la création User ID: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def create_api_key(self, user_id):
        """
        Étape 2: Créer l'API Key pour le User ID
        
        Args:
            user_id (str): User ID créé à l'étape 1
            
        Returns:
            dict: Résultat avec api_key créée
        """
        print(f"🔧 Création de l'API Key pour User ID: {user_id}")
        
        try:
            url = f"{self.base_url}/v1_0/apiuser/{user_id}/apikey"
            
            headers = {
                'Content-Type': 'application/json',
                'Ocp-Apim-Subscription-Key': self.subscription_key
            }
            
            print(f"🔗 URL: {url}")
            
            response = requests.post(url, headers=headers, timeout=30)
            
            print(f"📊 Status Code: {response.status_code}")
            
            if response.status_code == 201:
                api_key = response.json().get('apiKey')
                print("✅ API Key créée avec succès!")
                print(f"🔑 API Key: {api_key}")
                return {
                    'success': True,
                    'api_key': api_key,
                    'message': 'API Key créée avec succès'
                }
            else:
                print(f"❌ Erreur création API Key: {response.status_code}")
                print(f"📄 Réponse: {response.text}")
                return {
                    'success': False,
                    'error': f"Erreur {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            print(f"❌ Exception lors de la création API Key: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def test_credentials(self, user_id, api_key):
        """
        Étape 3: Tester les credentials créés
        
        Args:
            user_id (str): User ID à tester
            api_key (str): API Key à tester
            
        Returns:
            dict: Résultat du test
        """
        print(f"🧪 Test des credentials...")
        
        try:
            # Créer les credentials Base64 pour l'authentification
            credentials = f"{user_id}:{api_key}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            
            url = f"{self.base_url}/collection/token/"
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Basic {encoded_credentials}',
                'Ocp-Apim-Subscription-Key': self.subscription_key
            }
            
            print(f"🔗 URL: {url}")
            
            response = requests.post(url, headers=headers, timeout=30)
            
            print(f"📊 Status Code: {response.status_code}")
            
            if response.status_code == 200:
                token_data = response.json()
                print("✅ Test réussi! Token d'accès obtenu.")
                print(f"🎫 Token: {token_data.get('access_token', '')[:50]}...")
                return {
                    'success': True,
                    'token_data': token_data,
                    'message': 'Credentials valides'
                }
            else:
                print(f"❌ Échec du test: {response.status_code}")
                print(f"📄 Réponse: {response.text}")
                return {
                    'success': False,
                    'error': f"Test échoué: {response.status_code}"
                }
                
        except Exception as e:
            print(f"❌ Exception lors du test: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def setup_complete_credentials(self, callback_host="your-domain.com"):
        """
        Processus complet: Créer User ID + API Key + Test
        
        Args:
            callback_host (str): Votre domaine pour les callbacks
            
        Returns:
            dict: Tous les credentials créés
        """
        print("🚀 DÉBUT DU PROCESSUS DE CRÉATION MTN CREDENTIALS")
        print("=" * 60)
        
        # Étape 1: Créer User ID
        user_result = self.create_user_id(callback_host)
        if not user_result['success']:
            return user_result
        
        user_id = user_result['user_id']
        
        print("\n" + "=" * 60)
        
        # Étape 2: Créer API Key
        api_result = self.create_api_key(user_id)
        if not api_result['success']:
            return api_result
        
        api_key = api_result['api_key']
        
        print("\n" + "=" * 60)
        
        # Étape 3: Tester les credentials
        test_result = self.test_credentials(user_id, api_key)
        
        print("\n" + "=" * 60)
        print("🎉 PROCESSUS TERMINÉ!")
        print("=" * 60)
        
        if test_result['success']:
            print("✅ SUCCÈS COMPLET! Vos credentials MTN sont prêts.")
            print(f"\n📋 RÉSULTATS:")
            print(f"👤 MTN_COLLECTION_USER_ID={user_id}")
            print(f"🔑 MTN_COLLECTION_API_KEY={api_key}")
            print(f"🎫 MTN_COLLECTION_SUBSCRIPTION_KEY={self.subscription_key}")
            
            return {
                'success': True,
                'credentials': {
                    'user_id': user_id,
                    'api_key': api_key,
                    'subscription_key': self.subscription_key
                },
                'message': 'Credentials créés et testés avec succès'
            }
        else:
            print("⚠️ Credentials créés mais test échoué. Vérifiez la configuration.")
            return {
                'success': False,
                'error': 'Test des credentials échoué',
                'partial_credentials': {
                    'user_id': user_id,
                    'api_key': api_key
                }
            }

# ===============================================
# 2. SCRIPT D'EXÉCUTION
# ===============================================

def main():
    """Script principal pour créer les credentials MTN"""
    
    print("🎯 SCRIPT DE CRÉATION CREDENTIALS MTN MOBILE MONEY")
    print("=" * 60)
    
    # Configuration
    print("📋 Configuration initiale...")
    
    # Récupérer la subscription key depuis l'environnement ou saisie manuelle
    subscription_key = input("🔑 Entrez votre MTN Subscription Key (primaire ou secondaire): ").strip()
    
    if not subscription_key:
        print("❌ Subscription Key obligatoire!")
        return
    
    # Callback host (votre domaine)
    callback_host = input("🌐 Entrez votre domaine callback (ex: api.nsia.cg): ").strip()
    if not callback_host:
        callback_host = "api.nsia.cg"  # Valeur par défaut
    
    # Environnement
    environment = input("🏗️ Environnement (sandbox/production) [sandbox]: ").strip().lower()
    if not environment:
        environment = "sandbox"
    
    print(f"\n📊 Configuration:")
    print(f"   Subscription Key: {subscription_key[:10]}...")
    print(f"   Callback Host: {callback_host}")
    print(f"   Environnement: {environment}")
    
    confirm = input("\n✅ Continuer? (y/N): ").strip().lower()
    if confirm != 'y':
        print("❌ Annulé par l'utilisateur.")
        return
    
    # Créer le setup
    setup = MTNCredentialsSetup(subscription_key, environment)
    
    # Exécuter le processus complet
    result = setup.setup_complete_credentials(callback_host)
    
    if result['success']:
        print("\n🎊 FÉLICITATIONS! Vos credentials MTN sont prêts!")
        print("\n📝 Ajoutez ces lignes à votre fichier .env:")
        print("=" * 50)
        credentials = result['credentials']
        print(f"MTN_COLLECTION_USER_ID={credentials['user_id']}")
        print(f"MTN_COLLECTION_API_KEY={credentials['api_key']}")
        print(f"MTN_COLLECTION_SUBSCRIPTION_KEY={credentials['subscription_key']}")
        print(f"MTN_ENVIRONMENT={environment}")
        print("=" * 50)
    else:
        print(f"\n❌ Échec: {result['error']}")
        if 'partial_credentials' in result:
            print("\n⚠️ Credentials partiels créés:")
            partial = result['partial_credentials']
            print(f"   User ID: {partial['user_id']}")
            print(f"   API Key: {partial['api_key']}")


if __name__ == "__main__":
    main()
