from django.db import models
from apps.pass_clients.models import SouscriptionPass

class ProduitPass(models.Model):
    """Catalogue des produits PASS NSIA"""
    
    CATEGORIE_CHOICES = [
        ('accident', 'Accident'),
        ('sante', 'Santé'),
        ('epargne', 'Épargne'),
        ('funeraire', 'Funéraire'),
        ('mixte', 'Mixte')
    ]
    
    # Identification produit
    code_pass = models.CharField(max_length=20, unique=True)  # KIMIA, BATELA, SALISA
    nom_pass = models.CharField(max_length=100)
    description = models.TextField()
    categorie = models.CharField(max_length=30, choices=CATEGORIE_CHOICES)
    
    # Tarification
    prix_minimum = models.DecimalField(max_digits=10, decimal_places=2, default=100.00)
    prix_maximum = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Caractéristiques
    nombre_beneficiaires_max = models.IntegerField(default=6)
    duree_validite_jours = models.IntegerField(default=365)
    
    # Garanties (JSON pour flexibilité)
    garanties = models.JSONField(default=dict)
    
    # Souscription
    souscription_mobile_money = models.BooleanField(default=True)
    code_ussd = models.CharField(max_length=20, default='*128*6*6*1#')
    
    # Métadonnées
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    statut = models.CharField(
        max_length=20,
        choices=[('actif', 'Actif'), ('inactif', 'Inactif'), ('archive', 'Archivé')],
        default='actif'
    )

    class Meta:
        db_table = 'produits_pass'
        ordering = ['code_pass']
        verbose_name = 'Produit PASS'
        verbose_name_plural = 'Produits PASS'
        
    def __str__(self):
        return f"{self.code_pass} - {self.nom_pass}"

class BeneficiairePass(models.Model):
    """Bénéficiaires d'une souscription PASS (max 6)"""
    
    # Relations
    souscription_pass = models.ForeignKey(
        'pass_clients.SouscriptionPass', 
        on_delete=models.CASCADE, 
        related_name='beneficiaires'
    )
    
    # Informations bénéficiaire
    nom = models.CharField(max_length=60)
    prenom = models.CharField(max_length=60)
    telephone = models.CharField(max_length=25, blank=True)
    relation_souscripteur = models.CharField(max_length=30)  # conjoint, enfant, parent, etc.
    date_naissance = models.DateField(null=True, blank=True)
    
    # Priorité
    ordre_priorite = models.IntegerField(default=1)
    
    # Statut
    statut = models.CharField(
        max_length=20,
        choices=[('actif', 'Actif'), ('inactif', 'Inactif'), ('decede', 'Décédé')],
        default='actif'
    )
    date_ajout = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'beneficiaires_pass'
        ordering = ['souscription_pass', 'ordre_priorite']
        unique_together = [['souscription_pass', 'ordre_priorite']]
        verbose_name = 'Bénéficiaire PASS'
        verbose_name_plural = 'Bénéficiaires PASS'
        
    def __str__(self):
        return f"{self.prenom} {self.nom} ({self.relation_souscripteur})"
    
    def save(self, *args, **kwargs):
        # Vérification max 6 bénéficiaires
        if not self.pk:  # Nouvelle création
            count = BeneficiairePass.objects.filter(
                souscription_pass=self.souscription_pass
            ).count()
            if count >= 6:
                raise ValueError("Maximum 6 bénéficiaires autorisés par souscription PASS")
        super().save(*args, **kwargs)

