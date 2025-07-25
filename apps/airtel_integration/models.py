# apps/airtel_integration/models.py

from django.db import models
from django.core.validators import RegexValidator
from apps.pass_payments.models import PaiementPass
import uuid
from datetime import datetime

class TransactionAirtel(models.Model):
    """Log des transactions Airtel Money"""
    
    TYPE_TRANSACTION_CHOICES = [
        ('debit_request', 'Debit Request'),
        ('payment_status', 'Payment Status'),
        ('account_balance', 'Account Balance'),
        ('refund', 'Refund')
    ]
    
    STATUT_CHOICES = [
        ('initiated', 'Initiated'),
        ('pending', 'Pending'),
        ('successful', 'Successful'),
        ('failed', 'Failed'),
        ('timeout', 'Timeout'),
        ('cancelled', 'Cancelled')
    ]
    
    # Identification Airtel
    external_id = models.CharField(
        max_length=100, 
        unique=True,
        help_text="Notre identifiant de transaction"
    )
    airtel_transaction_id = models.CharField(
        max_length=100, 
        blank=True,
        help_text="ID de transaction retourné par Airtel"
    )
    
    # Relations
    paiement_pass = models.ForeignKey(
        PaiementPass,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='transactions_airtel'
    )
    
    # Type et détails
    type_transaction = models.CharField(
        max_length=20, 
        choices=TYPE_TRANSACTION_CHOICES,
        default='debit_request'
    )
    montant = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        help_text="Montant en XAF"
    )
    devise = models.CharField(max_length=3, default='XAF')
    
    # Numéros de téléphone
    payer_msisdn = models.CharField(
        max_length=15,
        validators=[RegexValidator(r'^\d{9,15}$', 'Format numéro invalide')],
        help_text="Numéro du payeur (format international sans +)"
    )
    payee_msisdn = models.CharField(
        max_length=15, 
        blank=True,
        help_text="Numéro du bénéficiaire"
    )
    
    # Statut et réponse Airtel
    statut = models.CharField(
        max_length=20, 
        choices=STATUT_CHOICES, 
        default='initiated'
    )
    status_reason = models.CharField(
        max_length=100, 
        blank=True,
        help_text="Raison du statut (en cas d'échec)"
    )
    
    # Réponses API Airtel (JSON)
    request_payload = models.JSONField(
        blank=True, null=True,
        help_text="Données envoyées à l'API Airtel"
    )
    response_payload = models.JSONField(
        blank=True, null=True,
        help_text="Réponse de l'API Airtel"
    )
    callback_payload = models.JSONField(
        blank=True, null=True,
        help_text="Données reçues du callback Airtel"
    )
    
    # Métadonnées
    reference_client = models.CharField(
        max_length=100, 
        default="NSIA PASS",
        help_text="Référence affichée côté client"
    )
    country = models.CharField(max_length=2, default='CG')
    
    # Timestamps
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    date_callback = models.DateTimeField(
        null=True, blank=True,
        help_text="Date de réception du callback"
    )
    
    class Meta:
        db_table = 'airtel_transactions'
        verbose_name = 'Transaction Airtel'
        verbose_name_plural = 'Transactions Airtel'
        ordering = ['-date_creation']
        indexes = [
            models.Index(fields=['external_id']),
            models.Index(fields=['airtel_transaction_id']),
            models.Index(fields=['statut']),
            models.Index(fields=['date_creation']),
        ]
    
    def __str__(self):
        return f"Airtel {self.external_id} - {self.statut}"
    
    @property
    def is_successful(self):
        """Vérifie si la transaction est réussie"""
        return self.statut == 'successful'
    
    @property
    def is_pending(self):
        """Vérifie si la transaction est en attente"""
        return self.statut in ['initiated', 'pending']
    
    @property
    def is_failed(self):
        """Vérifie si la transaction a échoué"""
        return self.statut in ['failed', 'timeout', 'cancelled']
    
    def update_from_callback(self, callback_data):
        """Met à jour la transaction depuis un callback Airtel"""
        self.callback_payload = callback_data
        self.date_callback = datetime.now()
        
        # Mapper le statut selon la réponse Airtel
        airtel_status = callback_data.get('status', '').upper()
        if airtel_status == 'SUCCESS':
            self.statut = 'successful'
        elif airtel_status == 'FAILED':
            self.statut = 'failed'
            self.status_reason = callback_data.get('message', 'Échec Airtel')
        elif airtel_status == 'PENDING':
            self.statut = 'pending'
        
        self.save()
        
        # Mettre à jour le PaiementPass associé
        if self.paiement_pass:
            if self.statut == 'successful':
                self.paiement_pass.statut = 'succes'
                self.paiement_pass.date_confirmation = datetime.now()
            elif self.statut == 'failed':
                self.paiement_pass.statut = 'echec'
                self.paiement_pass.motif_echec = self.status_reason
            
            self.paiement_pass.save()
    
    def save(self, *args, **kwargs):
        # Auto-génération de l'external_id si pas fourni
        if not self.external_id:
            date_str = datetime.now().strftime('%Y%m%d')
            unique_id = uuid.uuid4().hex[:8].upper()
            self.external_id = f"AIRTEL-{date_str}-{unique_id}"
        
        super().save(*args, **kwargs)