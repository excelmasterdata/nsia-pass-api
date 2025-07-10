from django.db import transaction
from django.utils import timezone
from apps.pass_clients.models import ClientPass, SouscriptionPass
from apps.pass_products.models import ProduitPass, BeneficiairePass
from apps.pass_payments.models import PaiementPass
import uuid



class SouscriptionPassService:
    """Service pour gérer le workflow de souscription PASS"""
    
    @staticmethod
    def creer_client_pass(donnees_client):
        """Créer ou récupérer un client PASS"""
        telephone = donnees_client['telephone']
        
        # Vérifier si le client existe déjà
        client, created = ClientPass.objects.get_or_create(
            telephone=telephone,
            defaults={
                'nom': donnees_client['nom'],
                'prenom': donnees_client['prenom'],
                'adresse': donnees_client.get('adresse', ''),
                'date_naissance': donnees_client.get('date_naissance'),
                'lieu_naissance': donnees_client.get('lieu_naissance', ''),
                'operateur_mobile': donnees_client.get('operateur_mobile'),
                'numero_mobile_money': donnees_client.get('numero_mobile_money', telephone),
                'statut': 'actif'
            }
        )
        
        if not created:
            # Mettre à jour les informations si nécessaire
            for field, value in donnees_client.items():
                if hasattr(client, field) and value:
                    setattr(client, field, value)
            client.save()
        
        return client, created

    @staticmethod
    @transaction.atomic
    def creer_souscription_pass(donnees_souscription):
        """Créer une nouvelle souscription PASS"""
        
        # 1. Récupérer ou créer le client
        client, client_created = SouscriptionPassService.creer_client_pass(
            donnees_souscription['client']
        )
        
        # 2. Récupérer le produit PASS
        try:
            produit = ProduitPass.objects.get(
                code_pass=donnees_souscription['code_pass'],
                statut='actif'
            )
        except ProduitPass.DoesNotExist:
            raise ValueError(f"Produit PASS {donnees_souscription['code_pass']} non trouvé")
        
        # 3. Valider le montant
        montant = donnees_souscription['montant_souscription']
        if montant < produit.prix_minimum:
            raise ValueError(f"Montant minimum: {produit.prix_minimum} FCFA")
        if produit.prix_maximum and montant > produit.prix_maximum:
            raise ValueError(f"Montant maximum: {produit.prix_maximum} FCFA")
        
        # 4. Créer la souscription
        souscription = SouscriptionPass.objects.create(
            client=client,
            produit_pass=produit,
            montant_souscription=montant,
            periodicite=donnees_souscription.get('periodicite', 'mensuelle'),
            statut='en_cours',
            validation_automatique=True,
            operateur_paiement=donnees_souscription.get('operateur_mobile', 'mtn'),
            commentaires=donnees_souscription.get('commentaires', '')
        )
        
        # 5. Ajouter les bénéficiaires si fournis
        beneficiaires_data = donnees_souscription.get('beneficiaires', [])
        beneficiaires_crees = []
        
        for i, beneficiaire_data in enumerate(beneficiaires_data[:6]):  # Max 6
            beneficiaire = BeneficiairePass.objects.create(
                souscription_pass=souscription,
                nom=beneficiaire_data['nom'],
                prenom=beneficiaire_data['prenom'],
                telephone=beneficiaire_data.get('telephone', ''),
                relation_souscripteur=beneficiaire_data['relation'],
                date_naissance=beneficiaire_data.get('date_naissance'),
                ordre_priorite=i + 1,
                statut='actif'
            )
            beneficiaires_crees.append(beneficiaire)
        
        return {
            'souscription': souscription,
            'client': client,
            'client_created': client_created,
            'beneficiaires': beneficiaires_crees
        }

    @staticmethod
    @transaction.atomic  
    def activer_souscription(souscription_id):
        """Activer une souscription après paiement validé"""
        
        try:
            souscription = SouscriptionPass.objects.get(id=souscription_id)
        except SouscriptionPass.DoesNotExist:
            raise ValueError("Souscription non trouvée")
        
        if souscription.statut != 'en_cours':
            raise ValueError("Seules les souscriptions 'en_cours' peuvent être activées")
        
        # Activer la souscription
        souscription.statut = 'activee'
        souscription.date_activation = timezone.now()
        
        # Calculer la date d'expiration
        duree = souscription.produit_pass.duree_validite_jours
        souscription.date_expiration = (
            souscription.date_activation + timezone.timedelta(days=duree)
        ).date()
        
        souscription.paiement_initial_recu = True
        souscription.save()
        
        # Mettre à jour les statistiques client
        client = souscription.client
        client.nombre_souscriptions_actives = client.souscriptions.filter(
            statut='activee'
        ).count()
        client.valeur_totale_souscriptions = sum(
            s.montant_souscription for s in client.souscriptions.filter(
                statut__in=['activee', 'en_cours']
            )
        )
        client.save()
        
        return souscription
