    def _get_access_token(self):
        """Récupère ou génère un token d'accès MTN"""
        # Vérifier le cache
        cached_token = cache.get('mtn_access_token')
        if cached_token:
            return cached_token
            
        # Générer un nouveau token
        try:
            url = f"{self.base_url}/collection/token/"
            
            # CORRECTION: Encoder correctement les credentials
            credentials = f"{self.user_id}:{self.api_key}"
            encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Basic {encoded_credentials}',  # ✅ Correction ici
                'Ocp-Apim-Subscription-Key': self.subscription_key,
            }
            
            response = requests.post(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            token_data = response.json()
            access_token = token_data.get('access_token')
            expires_in = token_data.get('expires_in', 3600)
            
            # Cache le token
            cache.set('mtn_access_token', access_token, expires_in - 600)
            
            return access_token
            
        except Exception as e:
            logger.error(f"Erreur génération token MTN: {e}")
            return None
