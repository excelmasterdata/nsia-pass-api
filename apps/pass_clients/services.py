from django.db import transaction
from django.utils import timezone
from apps.borne_auth.models import Agent, NumeroPolice
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
        
        agent = None
        if donnees_souscription.get('agent_id'):
            try:
                agent = Agent.objects.get(id=donnees_souscription['agent_id'], statut='actif')
            except Agent.DoesNotExist:
                pass  # Continuer sans agent si erreur
        
        # 4. Créer la souscription
        souscription = SouscriptionPass.objects.create(
            client=client,
            produit_pass=produit,
            montant_souscription=montant,
            periodicite=donnees_souscription.get('periodicite', 'mensuelle'),
            statut='en_cours',
            validation_automatique=True,
            operateur_paiement=donnees_souscription.get('operateur_mobile', 'mtn'),
            commentaires=donnees_souscription.get('commentaires', ''),
            agent=agent
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
                statut='actif',
                
            )
            beneficiaires_crees.append(beneficiaire)
        
        return {
            'souscription': souscription,
            'client': client,
            'client_created': client_created,
            'beneficiaires': beneficiaires_crees,
            'agent': agent  # ✅ Retourner l'agent aussi
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
        
        # Vérifier si la police n'existe pas déjà (éviter les doublons)
        police_existante = NumeroPolice.objects.filter(
            souscription_pass=souscription
        ).first()
        
        if police_existante:
            print(f"⚠️ Police déjà générée pour souscription {souscription_id}: {police_existante.numero_police}")
            return souscription
        
        # 1. Activer la souscription
        souscription.statut = 'activee'
        souscription.date_activation = timezone.now()

        # Quand souscription activée
        #if souscription.statut == 'activee' and souscription.agent:
        #commission = souscription.montant_souscription * souscription.agent.taux_commission / 100
        #souscription.agent.solde_commissions += commission
        #souscription.agent.save()
        
        # 2. Calculer la date d'expiration
        duree = souscription.produit_pass.duree_validite_jours
        souscription.date_expiration = (
            souscription.date_activation + timezone.timedelta(days=duree)
        ).date()
        
        # 3. Marquer le paiement initial comme reçu
        souscription.paiement_initial_recu = True
        souscription.save()
        
        # 4. NOUVEAU : Générer le numéro de police
        numero_police = SouscriptionPassService.generer_numero_police(souscription)
        
        # 5. Créer l'enregistrement NumeroPolice
        police = NumeroPolice.objects.create(
            souscription_pass=souscription,
            numero_police=numero_police,
            date_attribution=timezone.now(),
            statut='attribue'
        )
        
        print(f"✅ Police générée: {numero_police} pour souscription {souscription_id}")
        
        # 6. Mettre à jour les statistiques client
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
        
        return {
            'souscription': souscription,
            'numero_police': numero_police,
            'police': police
        }
    
    @staticmethod
    def generer_numero_police(souscription):
        """Génère un numéro de police unique au format CG-YYYY-PPP-NNN"""
        
        # Composants du numéro
        pays = "CG"  # Congo
        annee = timezone.now().year
        
        # Code produit (3 premières lettres du code_pass en majuscules)
        code_produit = souscription.produit_pass.code_pass[:3].upper()
        
        # Trouver le prochain numéro de séquence pour cette année et ce produit
        prefixe = f"{pays}-{annee}-{code_produit}-"
        
        # Chercher le dernier numéro généré avec ce préfixe
        dernier_numero = NumeroPolice.objects.filter(
            numero_police__startswith=prefixe
        ).order_by('-numero_police').first()
        
        if dernier_numero:
            # Extraire la séquence et incrémenter
            try:
                sequence_str = dernier_numero.numero_police.split('-')[-1]
                sequence = int(sequence_str) + 1
            except (ValueError, IndexError):
                # En cas d'erreur, commencer à 1
                sequence = 1
        else:
            # Premier numéro pour cette combinaison année/produit
            sequence = 1
        
        # Formater le numéro final
        numero_police = f"{prefixe}{sequence:03d}"
        
        print(f"🔢 Numéro de police généré: {numero_police}")
        
        return numero_police
    
    @staticmethod
    def verifier_police_unique(numero_police):
        """Vérifie qu'un numéro de police est unique"""
        return not NumeroPolice.objects.filter(
            numero_police=numero_police
        ).exists()
    
    @staticmethod
    def get_police_by_souscription(souscription_id):
        """Récupère la police d'une souscription"""
        try:
            police = NumeroPolice.objects.get(
                souscription_pass_id=souscription_id,
                statut='attribue'
            )
            return police.numero_police
        except NumeroPolice.DoesNotExist:
            return None
