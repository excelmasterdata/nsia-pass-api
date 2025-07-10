from django.db import models
from apps.pass_payments.models import PaiementPass
class TransactionMTN(models.Model):
    """Log des transactions MTN Mobile Money"""
    
    TYPE_TRANSACTION_CHOICES = [
        ('request_to_pay', 'Request to Pay'),
        ('payment_status', 'Payment Status'),
        ('account_balance', 'Account Balance'),
        ('account_holder', 'Account Holder'),
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
    
    # Identification MTN
    external_id = models.CharField(max_length=100, unique=True)  # Notre ID
    financial_transaction_id = models.CharField(max_length=100, blank=True)  # ID MTN
    
    # Relations
    paiement_pass = models.ForeignKey(
        PaiementPass,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='transactions_mtn'
    )
    
    # Type et détails
    type_transaction = models.CharField(max_length=20, choices=TYPE_TRANSACTION_CHOICES)
    montant = models.DecimalField(max_digits=10, decimal_places=2)
    devise = models.CharField(max_length=3, default='XAF')
    
    # Numéros de téléphone
    payer_msisdn = models.CharField(max_length=15)  # Format international
    payee_msisdn = models.CharField(max_length=15, blank=True)
    
    # Statut et réponse MTN
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='initiated')
    status_reason = models.CharField(max_length=100, blank=True)
    
    # Réponses API MTN (JSON)
    request_payload = models.JSONField(default=dict)
    response_payload = models.JSONField(default=dict)
    callback_payload = models.JSONField(default=dict)
    
    # Dates
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    date_expiration = models.DateTimeField(null=True, blank=True)
    
    # Retry et debugging
    nombre_tentatives = models.IntegerField(default=0)
    derniere_erreur = models.TextField(blank=True)

    class Meta:
        db_table = 'transactions_mtn'
        ordering = ['-date_creation']
        verbose_name = 'Transaction MTN'
        verbose_name_plural = 'Transactions MTN'
        
    def __str__(self):
        return f"{self.external_id} - {self.montant} XAF ({self.statut})"

class ConfigurationMTN(models.Model):
    """Configuration MTN Mobile Money par environnement"""
    
    ENVIRONNEMENT_CHOICES = [
        ('sandbox', 'Sandbox'),
        ('production', 'Production')
    ]
    
    # Environnement
    environnement = models.CharField(max_length=20, choices=ENVIRONNEMENT_CHOICES, unique=True)
    
    # URLs API MTN
    base_url = models.URLField()
    collection_url = models.URLField()
    
    # Credentials
    user_id = models.CharField(max_length=100)
    api_key = models.CharField(max_length=100)
    subscription_key = models.CharField(max_length=100)
    
    # Configuration pays
    currency = models.CharField(max_length=3, default='XAF')
    country_code = models.CharField(max_length=2, default='CG')
    
    # Paramètres
    timeout_seconds = models.IntegerField(default=30)
    max_retries = models.IntegerField(default=3)
    
    # Statut
    actif = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'configurations_mtn'
        verbose_name = 'Configuration MTN'
        verbose_name_plural = 'Configurations MTN'
        
    def __str__(self):
        return f"MTN {self.environnement} - {'Actif' if self.actif else 'Inactif'}"

class LogMTN(models.Model):
    """Logs détaillés des appels API MTN"""
    
    NIVEAU_CHOICES = [
        ('DEBUG', 'Debug'),
        ('INFO', 'Info'),
        ('WARNING', 'Warning'),
        ('ERROR', 'Error'),
        ('CRITICAL', 'Critical')
    ]
    
    # Contexte
    transaction_mtn = models.ForeignKey(
        TransactionMTN,
        on_delete=models.CASCADE,
        related_name='logs'
    )
    
    # Log details
    niveau = models.CharField(max_length=10, choices=NIVEAU_CHOICES)
    message = models.TextField()
    
    # Request/Response
    method = models.CharField(max_length=10, blank=True)  # GET, POST, PUT
    url = models.URLField(blank=True)
    headers = models.JSONField(default=dict)
    request_body = models.JSONField(default=dict)
    response_status = models.IntegerField(null=True, blank=True)
    response_body = models.JSONField(default=dict)
    
    # Timing
    duration_ms = models.IntegerField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'logs_mtn'
        ordering = ['-timestamp']
        verbose_name = 'Log MTN'
        verbose_name_plural = 'Logs MTN'
        
    def __str__(self):
        return f"{self.niveau} - {self.transaction_mtn.external_id} - {self.timestamp}"

