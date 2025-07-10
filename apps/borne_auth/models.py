from django.db import models

class NumeroPolice(models.Model):
    """Attribution des numéros de police Congo aux souscriptions PASS"""
    
    MODE_CHOICES = [
        ('automatique', 'Automatique'),
        ('manuel', 'Manuel')
    ]
    
    # Relations
    souscription_pass = models.OneToOneField(
        'pass_clients.SouscriptionPass',
        on_delete=models.CASCADE,
        related_name='numero_police'
    )
    agent_attribueur = models.ForeignKey(
        'auth.User',  # Ou créer un modèle Agent si nécessaire
        on_delete=models.SET_NULL,
        null=True, blank=True
    )
    
    # Numéro de police
    numero_police = models.CharField(max_length=20, unique=True)
    
    # Métadonnées
    date_attribution = models.DateTimeField(auto_now_add=True)
    mode_attribution = models.CharField(max_length=20, choices=MODE_CHOICES, default='automatique')
    commentaire_attribution = models.TextField(blank=True)
    
    # Statut
    statut = models.CharField(
        max_length=20,
        choices=[('attribue', 'Attribué'), ('suspendu', 'Suspendu'), ('annule', 'Annulé')],
        default='attribue'
    )

    class Meta:
        db_table = 'numeros_police_congo'
        ordering = ['-date_attribution']
        verbose_name = 'Numéro de Police'
        verbose_name_plural = 'Numéros de Police'
        
    def __str__(self):
        return f"{self.numero_police} - {self.souscription_pass.client.nom_complet}"

class Agent(models.Model):
    """Agents NSIA pour attribution manuelle des polices"""
    
    # Informations agent
    nom = models.CharField(max_length=60)
    prenom = models.CharField(max_length=60)
    telephone = models.CharField(max_length=25, unique=True)
    email = models.CharField(max_length=100, unique=True, null=True, blank=True)
    
    # Informations professionnelles
    matricule = models.CharField(max_length=20, unique=True)
    agence = models.CharField(max_length=100)
    poste = models.CharField(max_length=50, default='Agent Commercial')
    
    # Adresse
    adresse = models.TextField(blank=True)
    
    # Commissions
    solde_commissions = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    taux_commission = models.DecimalField(max_digits=5, decimal_places=2, default=5.00)
    
    # Métadonnées
    date_embauche = models.DateField()
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    statut = models.CharField(
        max_length=20,
        choices=[('actif', 'Actif'), ('inactif', 'Inactif'), ('suspendu', 'Suspendu')],
        default='actif'
    )

    class Meta:
        db_table = 'agents'
        ordering = ['nom', 'prenom']
        verbose_name = 'Agent NSIA'
        verbose_name_plural = 'Agents NSIA'
        
    def __str__(self):
        return f"{self.matricule} - {self.prenom} {self.nom}"
    
    @property
    def nom_complet(self):
        return f"{self.prenom} {self.nom}"

