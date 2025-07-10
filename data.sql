# ===============================================
# MODÈLES MANQUANTS - NSIA PASS API
# ===============================================

# ===============================================
# 1. MODÈLES PAIEMENTS - apps/pass_payments/models.py
# ===============================================

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
    type_paiement = models.CharField(max_length=20, choices=TYPE_PAIEMENT_CHOICES, default='cotisation')
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
        'django.contrib.auth.User',
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

# ===============================================
# 2. MODÈLES MTN INTEGRATION - apps/mtn_integration/models.py
# ===============================================

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

# ===============================================
# 3. MODÈLE AGENTS (optionnel) - apps/borne_auth/models.py (AJOUT)
# ===============================================

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

# ===============================================
# 4. MISE À JOUR NUMÉRO POLICE (avec Agent)
# ===============================================

# Modifier le modèle NumeroPolice dans apps/borne_auth/models.py:

# Remplacer cette ligne:
# agent_attribueur = models.ForeignKey('django.contrib.auth.User', ...)

# Par:
# agent_attribueur = models.ForeignKey(Agent, on_delete=models.SET_NULL, null=True, blank=True)

# ===============================================
# 5. COMMANDES FINALES
# ===============================================

"""
# Créer toutes les migrations manquantes
python manage.py makemigrations pass_payments
python manage.py makemigrations mtn_integration

# Mettre à jour borne_auth si modifié
python manage.py makemigrations borne_auth

# Appliquer toutes les migrations
python manage.py migrate

# Créer superuser
python manage.py createsuperuser
"""

# ===============================================
# NSIA PASS API - Configuration & Modèles
# ===============================================

# ===============================================
# 1. SETTINGS.PY - Configuration spécialisée PASS
# ===============================================

# nsia_pass_api/settings.py
import os
from pathlib import Path
from decouple import config
from datetime import timedelta

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent

# Security
SECRET_KEY = config('SECRET_KEY', default='nsia-pass-django-secret-key-congo-2024')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=lambda v: [s.strip() for s in v.split(',')])

# Application definition - Spécialisé PASS
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    
    # NSIA PASS Apps
    'apps.pass_clients.apps.PassClientsConfig',
    'apps.pass_products.apps.PassProductsConfig',
    'apps.pass_payments.apps.PassPaymentsConfig',
    'apps.borne_auth.apps.BorneAuthConfig',
    'apps.mtn_integration.apps.MtnIntegrationConfig',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'nsia_pass_api.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'nsia_pass_api.wsgi.application'

# Database PostgreSQL pour PASS
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='NSIAPassDB'),
        'USER': config('DB_USER', default='nsia_pass_user'),
        'PASSWORD': config('DB_PASSWORD', default='nsia_pass_password_123'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# REST Framework pour API PASS
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20
}

# JWT Configuration pour borne PASS
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),  # Session borne courte
    'REFRESH_TOKEN_LIFETIME': timedelta(hours=1),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}

# CORS pour frontend borne
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
CORS_ALLOW_CREDENTIALS = True

# Internationalization Congo
LANGUAGE_CODE = config('LANGUAGE_CODE', default='fr-fr')
TIME_ZONE = config('TIME_ZONE', default='Africa/Brazzaville')
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files  
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ===============================================
# Configuration MTN Mobile Money Congo
# ===============================================
MTN_MOBILE_MONEY = {
    'BASE_URL': config('MTN_API_BASE_URL', default='https://sandbox.momodeveloper.mtn.com'),
    'COLLECTION_USER_ID': config('MTN_COLLECTION_USER_ID', default=''),
    'COLLECTION_API_KEY': config('MTN_COLLECTION_API_KEY', default=''),
    'COLLECTION_SUBSCRIPTION_KEY': config('MTN_COLLECTION_SUBSCRIPTION_KEY', default=''),
    'ENVIRONMENT': config('MTN_ENVIRONMENT', default='sandbox'),  # sandbox ou production
    'CURRENCY': 'XAF',  # Franc CFA
    'COUNTRY': 'CG',    # Congo
}

# Redis pour Celery (tâches async)
CELERY_BROKER_URL = config('REDIS_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('REDIS_URL', default='redis://localhost:6379/0')

# ===============================================
# 2. MODÈLES PASS - apps/pass_clients/models.py
# ===============================================

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
    client = models.ForeignKey(ClientPass, on_delete=models.RESTRICT, related_name='souscriptions')
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

# ===============================================
# 3. MODÈLES PRODUITS - apps/pass_products/models.py
# ===============================================

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
        SouscriptionPass, 
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

# ===============================================
# 4. MODÈLE NUMÉROS POLICE - apps/borne_auth/models.py
# ===============================================

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
        'django.contrib.auth.User',  # Ou créer un modèle Agent si nécessaire
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

# ===============================================
# 5. COMMANDES POUR APPLIQUER LES MODÈLES
# ===============================================

"""
# 1. Créer les migrations
python manage.py makemigrations pass_clients
python manage.py makemigrations pass_products  
python manage.py makemigrations borne_auth

# 2. Appliquer les migrations
python manage.py migrate

# 3. Créer un superuser
python manage.py createsuperuser

# 4. Charger les données de test
python manage.py shell
# Puis exécuter le script de création des produits PASS
"""