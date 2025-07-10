from django.core.management.base import BaseCommand
from apps.pass_products.models import ProduitPass

class Command(BaseCommand):
    help = 'Charge les produits PASS NSIA de base'

    def handle(self, *args, **options):
        """Création des 3 produits PASS selon le PDF"""
        
        # ✅ PASS KIMIA - Pack accident + frais funéraires
        kimia, created = ProduitPass.objects.get_or_create(
            code_pass='KIMIA',
            defaults={
                'nom_pass': 'PASS KIMIA',
                'description': 'Pack accident + frais funéraires via Airtel Money',
                'categorie': 'accident',
                'prix_minimum': 100.00,
                'prix_maximum': 10000.00,
                'nombre_beneficiaires_max': 6,
                'duree_validite_jours': 365,
                'garanties': {
                    'individuel_accident': True,
                    'frais_medicaux_forfaitaires': True,
                    'indemnite_journaliere': True,
                    'mosungui_frais_funeraires': True,
                    'couverture_beneficiaires': 6,
                    'delai_prise_en_charge': 'immediat'
                },
                'souscription_mobile_money': True,
                'code_ussd': '*128*6*6*1#',
                'statut': 'actif'
            }
        )
        self.stdout.write(f"✅ PASS KIMIA {'créé' if created else 'existe déjà'}")

        # ✅ PASS BATELA - Épargne retraite + frais funéraires  
        batela, created = ProduitPass.objects.get_or_create(
            code_pass='BATELA',
            defaults={
                'nom_pass': 'PASS BATELA',
                'description': 'Épargne retraite + frais funéraires',
                'categorie': 'epargne',
                'prix_minimum': 100.00,
                'prix_maximum': 50000.00,
                'nombre_beneficiaires_max': 6,
                'duree_validite_jours': 365,
                'garanties': {
                    'epargne_retraite': True,
                    'taux_remuneration': 3.5,  # 3,5% par an
                    'capital_securise': True,
                    'versements_flexibles': True,
                    'mosungui_frais_funeraires': True,
                    'disponibilite_age_retraite': True
                },
                'souscription_mobile_money': True,
                'code_ussd': '*128*6*6*1#',
                'statut': 'actif'
            }
        )
        self.stdout.write(f"✅ PASS BATELA {'créé' if created else 'existe déjà'}")

        # ✅ PASS SALISA - Forfaits hospitaliers + frais funéraires
        salisa, created = ProduitPass.objects.get_or_create(
            code_pass='SALISA',
            defaults={
                'nom_pass': 'PASS SALISA',
                'description': 'Forfaits hospitaliers + frais funéraires',
                'categorie': 'sante',
                'prix_minimum': 100.00,
                'prix_maximum': 15000.00,
                'nombre_beneficiaires_max': 6,
                'duree_validite_jours': 365,
                'garanties': {
                    'forfaits_hospitaliers': True,
                    'prise_en_charge_frais_medicaux': True,
                    'indemnite_journaliere': True,
                    'couverture_hospitalisation': True,
                    'mosungui_frais_funeraires': True,
                    'prise_en_charge_immediate': True
                },
                'souscription_mobile_money': True,
                'code_ussd': '*128*6*6*1#',
                'statut': 'actif'
            }
        )
        self.stdout.write(f"✅ PASS SALISA {'créé' if created else 'existe déjà'}")

        self.stdout.write(
            self.style.SUCCESS('🎉 Tous les produits PASS NSIA ont été créés avec succès !')
        )