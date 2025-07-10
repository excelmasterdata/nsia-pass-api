from django.db import transaction
from django.utils import timezone
from apps.pass_payments.models import PaiementPass
from apps.pass_clients.services import SouscriptionPassService
import uuid

class PaiementPassService:
    """Service pour gérer les paiements PASS"""
    
    @staticmethod
    @transaction.atomic
    def initier_paiement_souscription(souscription, donnees_paiement):
        """Initier un paiement pour une souscription PASS"""
        
        # Générer un ID de transaction unique
        numero_transaction = f"NSIA-{uuid.uuid4().hex[:8].upper()}"
        
        # Créer l'enregistrement de paiement
        paiement = PaiementPass.objects.create(
            souscription_pass=souscription,
            client=souscription.client,
            numero_transaction=numero_transaction,
            montant=souscription.montant_souscription,
            frais_transaction=donnees_paiement.get('frais_transaction', 0),
            devise='XAF',
            operateur=donnees_paiement['operateur'],
            numero_payeur=donnees_paiement['numero_payeur'],
            statut='en_cours',
            type_paiement='souscription_initiale',
            commentaires=f"Paiement initial {souscription.produit_pass.nom_pass}"
        )
        
        return paiement
    
    @staticmethod
    @transaction.atomic
    def confirmer_paiement(numero_transaction, donnees_confirmation):
        """Confirmer un paiement reçu"""
        
        try:
            paiement = PaiementPass.objects.get(numero_transaction=numero_transaction)
        except PaiementPass.DoesNotExist:
            raise ValueError("Paiement non trouvé")
        
        if paiement.statut != 'en_cours':
            raise ValueError("Paiement déjà traité")
        
        # Mettre à jour le paiement
        paiement.statut = 'succes'
        paiement.reference_mobile_money = donnees_confirmation.get('reference_mtn')
        paiement.code_confirmation = donnees_confirmation.get('code_confirmation')
        paiement.date_confirmation = timezone.now()
        paiement.date_comptabilisation = timezone.now()
        paiement.save()
        
        # Activer la souscription
        souscription_activee = SouscriptionPassService.activer_souscription(
            paiement.souscription_pass.id
        )
        
        return {
            'paiement': paiement,
            'souscription': souscription_activee
        }
