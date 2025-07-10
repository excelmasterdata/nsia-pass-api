from django.db import models
from django.core.validators import RegexValidator

class PaiementPass(models.Model):
    """Historique des paiements PASS via Mobile Money"""
    
    OPERATEUR_CHOICES = [
        ('airtel_money', 'Airtel Money'),
        ('mtn_money', 'MTN Mobile Money'),
        ('moov_money', 'Moov Money'),
        ('orange_money', 'Orange Money'),
        ('wave', 'Wave'),
        ('especes', 'Espèces'),
        ('cheque', 'Chèque'),
        ('virement', 'Virement bancaire'),
        ('carte_bancaire', 'Carte bancaire'),
    ]
    
    STATUT_CHOICES = [
        ('en_cours', 'En cours'),
        ('succes', 'Succès'),
        ('echec', 'Échec'),
        ('rembourse', 'Remboursé'),
        ('en_verification', 'En vérification'),
        ('expire', 'Expiré')
    ]
    
    TYPE_PAIEMENT_CHOICES = [
        ('souscription_initiale', 'Souscription initiale'),
        ('cotisation', 'Cotisation'),
        ('renouvellement', 'Renouvellement'),
        ('rattrapage', 'Rattrapage')
    ]
    
    # Relations
    souscription_pass = models.ForeignKey(
        'pass_clients.SouscriptionPass',
        on_delete=models.RESTRICT,
        related_name='paiements'
    )
    client = models.ForeignKey(
        'pass_clients.ClientPass',
        on_delete=models.RESTRICT,
        related_name='paiements'
    )
    
    # Identification paiement
    numero_transaction = models.CharField(max_length=50, unique=True)
    reference_mobile_money = models.CharField(max_length=100, blank=True)
    
    # Montant
    montant = models.DecimalField(max_digits=10, decimal_places=2)
    frais_transaction = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    montant_net = models.DecimalField(max_digits=10, decimal_places=2)  # montant - frais
    devise = models.CharField(max_length=3, default='XAF')
    
    # Mobile Money spécifique
    operateur = models.CharField(max_length=20, choices=OPERATEUR_CHOICES)
    numero_payeur = models.CharField(
        max_length=25,
        validators=[RegexValidator(
            regex=r'^\+242[0-9]{8,9}$',
            message='Format téléphone Congo: +242XXXXXXXX'
        )]
    )
    code_confirmation = models.CharField(max_length=20, blank=True)
    
    # Statut paiement
    statut = models.CharField(max_length=30, choices=STATUT_CHOICES, default='en_cours')
    motif_echec = models.TextField(blank=True)
    
    # Dates
    date_paiement = models.DateTimeField(auto_now_add=True)
    date_confirmation = models.DateTimeField(null=True, blank=True)
    date_comptabilisation = models.DateTimeField(null=True, blank=True)
    
    # Type et métadonnées
    type_paiement = models.CharField(max_length=25, choices=TYPE_PAIEMENT_CHOICES, default='cotisation')
    commentaires = models.TextField(blank=True)
    
    # Traçabilité
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'paiements_pass'
        ordering = ['-date_paiement']
        verbose_name = 'Paiement PASS'
        verbose_name_plural = 'Paiements PASS'
        
    def __str__(self):
        return f"{self.numero_transaction} - {self.montant} XAF ({self.operateur})"
    
    def save(self, *args, **kwargs):
        # Calcul automatique du montant net
        self.montant_net = self.montant - self.frais_transaction
        super().save(*args, **kwargs)

class SinistrePass(models.Model):
    """Déclarations et prestations des sinistres PASS"""
    
    TYPE_SINISTRE_CHOICES = [
        ('accident', 'Accident'),
        ('hospitalisation', 'Hospitalisation'),
        ('deces', 'Décès'),
        ('frais_medicaux', 'Frais médicaux'),
        ('indemnite_journaliere', 'Indemnité journalière'),
        ('frais_funeraires', 'Frais funéraires'),
        ('epargne_retraite', 'Épargne retraite')
    ]
    
    STATUT_CHOICES = [
        ('declare', 'Déclaré'),
        ('en_instruction', 'En instruction'),
        ('valide', 'Validé'),
        ('rejete', 'Rejeté'),
        ('paye', 'Payé'),
        ('clos', 'Clos')
    ]
    
    # Relations
    souscription_pass = models.ForeignKey(
        'pass_clients.SouscriptionPass',
        on_delete=models.RESTRICT,
        related_name='sinistres'
    )
    beneficiaire = models.ForeignKey(
        'pass_products.BeneficiairePass',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='sinistres'
    )
    
    # Identification
    numero_sinistre = models.CharField(max_length=30, unique=True)
    
    # Type et description
    type_sinistre = models.CharField(max_length=50, choices=TYPE_SINISTRE_CHOICES)
    description_sinistre = models.TextField()
    lieu_sinistre = models.CharField(max_length=200, blank=True)
    date_sinistre = models.DateField()
    
    # Montants
    montant_demande = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    montant_accorde = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    
    # Workflow
    statut = models.CharField(max_length=30, choices=STATUT_CHOICES, default='declare')
    motif_rejet = models.TextField(blank=True)
    
    # Documents
    documents_requis = models.JSONField(default=list)
    documents_recus = models.JSONField(default=list)
    
    # Dates de traitement
    date_declaration = models.DateTimeField(auto_now_add=True)
    date_validation = models.DateTimeField(null=True, blank=True)
    date_paiement = models.DateTimeField(null=True, blank=True)
    
    # Instruction
    commentaires_instruction = models.TextField(blank=True)
    instructeur = models.ForeignKey(
    'auth.User',
    on_delete=models.SET_NULL,
    null=True, blank=True,
    related_name='sinistres_instruits'
)

    class Meta:
        db_table = 'sinistres_pass'
        ordering = ['-date_declaration']
        verbose_name = 'Sinistre PASS'
        verbose_name_plural = 'Sinistres PASS'
        
    def __str__(self):
        return f"{self.numero_sinistre} - {self.type_sinistre}"
    
    def save(self, *args, **kwargs):
        # Auto-génération du numéro de sinistre
        if not self.numero_sinistre:
            from datetime import datetime
            year = datetime.now().year
            count = SinistrePass.objects.filter(
                date_declaration__year=year
            ).count() + 1
            self.numero_sinistre = f"SIN-{year}-{count:06d}"
        super().save(*args, **kwargs)
