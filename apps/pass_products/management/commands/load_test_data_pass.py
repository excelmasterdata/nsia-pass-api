from django.core.management.base import BaseCommand
from apps.pass_clients.services import SouscriptionPassService
from apps.pass_payments.services import PaiementPassService
from datetime import date

class Command(BaseCommand):
    help = 'Charge des données de test PASS'

    def handle(self, *args, **options):
        """Créer des souscriptions de test"""
        
        # ✅ Client 1: Jean Baptiste KONGO
        donnees_souscription_1 = {
            'client': {
                'nom': 'KONGO',
                'prenom': 'Jean Baptiste',
                'telephone': '+242061234567',
                'adresse': 'Poto-Poto, Brazzaville',
                'date_naissance': date(1985, 3, 15),
                'lieu_naissance': 'Pointe-Noire',
                'operateur_mobile': 'mtn'
            },
            'code_pass': 'KIMIA',
            'montant_souscription': 5000.00,
            'periodicite': 'mensuelle',
            'operateur_mobile': 'mtn_money',
            'beneficiaires': [
                {
                    'nom': 'KONGO',
                    'prenom': 'Marie',
                    'relation': 'conjoint',
                    'telephone': '+242061234568'
                },
                {
                    'nom': 'KONGO', 
                    'prenom': 'Junior',
                    'relation': 'enfant',
                    'date_naissance': date(2010, 7, 20)
                }
            ]
        }
        
        # Créer la souscription KIMIA
        resultat_1 = SouscriptionPassService.creer_souscription_pass(donnees_souscription_1)
        self.stdout.write(f"✅ Souscription KIMIA créée: {resultat_1['souscription'].numero_souscription}")
        
        # ✅ Client 2: Marie Claire MOUKOKO  
        donnees_souscription_2 = {
            'client': {
                'nom': 'MOUKOKO',
                'prenom': 'Marie Claire',
                'telephone': '+242059876543',
                'adresse': 'Bacongo, Brazzaville',
                'operateur_mobile': 'airtel'
            },
            'code_pass': 'SALISA',
            'montant_souscription': 7500.00,
            'periodicite': 'trimestrielle',
            'operateur_mobile': 'airtel_money',
            'beneficiaires': [
                {
                    'nom': 'MOUKOKO',
                    'prenom': 'André',
                    'relation': 'enfant'
                }
            ]
        }
        
        resultat_2 = SouscriptionPassService.creer_souscription_pass(donnees_souscription_2)
        self.stdout.write(f"✅ Souscription SALISA créée: {resultat_2['souscription'].numero_souscription}")

        self.stdout.write(
            self.style.SUCCESS('🎉 Données de test PASS créées avec succès !')
        )
