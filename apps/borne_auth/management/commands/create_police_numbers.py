from django.core.management.base import BaseCommand
from apps.pass_clients.models import SouscriptionPass
from apps.borne_auth.models import NumeroPolice
from datetime import datetime

class Command(BaseCommand):
    help = 'Créer les numéros de police pour les souscriptions PASS existantes'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Recréer les polices même si elles existent déjà'
        )
    
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🚀 Création des numéros de police PASS...')
        )
        
        # Filtrer les souscriptions
        if options['force']:
            souscriptions = SouscriptionPass.objects.all()
            # Supprimer les polices existantes si --force
            NumeroPolice.objects.all().delete()
            self.stdout.write(
                self.style.WARNING('⚠️  Polices existantes supprimées (--force)')
            )
        else:
            souscriptions = SouscriptionPass.objects.filter(
                numero_police__isnull=True
            )
        
        souscriptions = souscriptions.select_related('produit_pass', 'client')
        
        if not souscriptions.exists():
            self.stdout.write(
                self.style.WARNING('❌ Aucune souscription sans police trouvée')
            )
            return
        
        # Créer les polices
        compteurs = {'ACC': 1, 'EPG': 1, 'SAN': 1, 'GEN': 1}
        annee = datetime.now().year
        polices_creees = 0
        
        for souscription in souscriptions:
            # Type selon produit PASS
            produit_code = souscription.produit_pass.code_pass.upper()
            
            if 'KIMIA' in produit_code:
                type_police = 'ACC'
            elif 'BATELA' in produit_code:
                type_police = 'EPG'
            elif 'SALISA' in produit_code:
                type_police = 'SAN'
            else:
                type_police = 'GEN'
            
            numero_police = f"CG-{annee}-{type_police}-{compteurs[type_police]:03d}"
            compteurs[type_police] += 1
            
            # Créer la police
            NumeroPolice.objects.create(
                souscription_pass=souscription,
                numero_police=numero_police,
                mode_attribution='automatique',
                commentaire_attribution=f'Attribution automatique {produit_code}',
                statut='attribue'
            )
            
            polices_creees += 1
            
            self.stdout.write(
                f"✅ {numero_police} → {souscription.client.nom_complet}"
            )
        
        self.stdout.write(
            self.style.SUCCESS(f'\n🎉 {polices_creees} polices créées avec succès!')
        )
        
        # Afficher identifiants de test
        premiere_police = NumeroPolice.objects.first()
        if premiere_police:
            client = premiere_police.souscription_pass.client
            self.stdout.write(
                self.style.SUCCESS('\n📋 IDENTIFIANTS DE TEST:')
            )
            self.stdout.write(f"Police: {premiere_police.numero_police}")
            self.stdout.write(f"Téléphone: {client.telephone}")
