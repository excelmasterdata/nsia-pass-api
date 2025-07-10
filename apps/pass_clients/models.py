from django.db import models
from django.core.validators import RegexValidator

class ClientPass(models.Model):
    """Clients souscripteurs PASS Congo"""
    
    # Informations personnelles
    nom = models.CharField(max_length=60)
    prenom = models.CharField(max_length=60)
    telephone = models.CharField(
        max_length=25, 
        unique=True,
        validators=[RegexValidator(
            regex=r'^\+242[0-9]{8,9}$',
            message='Format téléphone Congo: +242XXXXXXXX'
        )]
    )
    date_naissance = models.DateField(null=True, blank=True)
    lieu_naissance = models.CharField(max_length=100, blank=True)
    adresse = models.TextField()
    
    # Mobile Money spécifique
    operateur_mobile = models.CharField(
        max_length=20, 
        choices=[
            ('airtel', 'Airtel'),
            ('mtn', 'MTN'),
            ('moov', 'Moov')
        ],
        null=True, blank=True
    )
    numero_mobile_money = models.CharField(max_length=25, blank=True)
    
    # Statistiques
    nombre_souscriptions_actives = models.IntegerField(default=0)
    valeur_totale_souscriptions = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    # Métadonnées
    date_premiere_souscription = models.DateTimeField(auto_now_add=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    statut = models.CharField(
        max_length=20, 
        choices=[('actif', 'Actif'), ('inactif', 'Inactif'), ('suspendu', 'Suspendu')],
        default='actif'
    )

    class Meta:
        db_table = 'clients_pass'
        ordering = ['nom', 'prenom']
        verbose_name = 'Client PASS'
        verbose_name_plural = 'Clients PASS'
        
    def __str__(self):
        return f"{self.prenom} {self.nom} - {self.telephone}"
    
    @property
    def nom_complet(self):
        return f"{self.prenom} {self.nom}"

class SouscriptionPass(models.Model):
    """Souscriptions PASS autonomes via Mobile Money"""
    
    STATUT_CHOICES = [
        ('en_cours', 'En cours'),
        ('activee', 'Activée'),
        ('suspendue', 'Suspendue'),
        ('expiree', 'Expirée'),
        ('annulee', 'Annulée'),
        ('convertie_en_contrat', 'Convertie en contrat')
    ]
    
    PERIODICITE_CHOICES = [
        ('hebdomadaire', 'Hebdomadaire'),
        ('mensuelle', 'Mensuelle'),
        ('trimestrielle', 'Trimestrielle'),
        ('annuelle', 'Annuelle'),
        ('unique', 'Paiement unique')
    ]
    
    # Relations
    client = models.ForeignKey('pass_clients.ClientPass', on_delete=models.RESTRICT, related_name='souscriptions')
    produit_pass = models.ForeignKey('pass_products.ProduitPass', on_delete=models.RESTRICT)
    
    # Identification
    numero_souscription = models.CharField(max_length=30, unique=True)
    
    # Conditions financières
    montant_souscription = models.DecimalField(max_digits=10, decimal_places=2)
    periodicite = models.CharField(max_length=20, choices=PERIODICITE_CHOICES, default='mensuelle')
    
    # Workflow PASS
    statut = models.CharField(max_length=30, choices=STATUT_CHOICES, default='en_cours')
    validation_automatique = models.BooleanField(default=True)
    paiement_initial_recu = models.BooleanField(default=False)
    
    # Dates
    date_souscription = models.DateTimeField(auto_now_add=True)
    date_activation = models.DateTimeField(null=True, blank=True)
    date_expiration = models.DateField(null=True, blank=True)
    
    # Mobile Money
    transaction_mobile_money = models.CharField(max_length=50, blank=True)
    operateur_paiement = models.CharField(max_length=20, blank=True)
    
    # Métadonnées
    commentaires = models.TextField(blank=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'souscriptions_pass'
        ordering = ['-date_souscription']
        verbose_name = 'Souscription PASS'
        verbose_name_plural = 'Souscriptions PASS'
        
    def __str__(self):
        return f"{self.numero_souscription} - {self.client.nom_complet}"
    
    def save(self, *args, **kwargs):
        # Auto-génération du numéro de souscription
        if not self.numero_souscription:
            from datetime import datetime
            year = datetime.now().year
            count = SouscriptionPass.objects.filter(
                date_souscription__year=year
            ).count() + 1
            self.numero_souscription = f"PASS-{self.produit_pass.code_pass}-{year}-{count:06d}"
        super().save(*args, **kwargs)
