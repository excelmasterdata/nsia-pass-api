import os
from pathlib import Path
from decouple import config
from datetime import timedelta
from celery.schedules import crontab

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
    'apps.airtel_integration.apps.AirtelIntegrationConfig',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # ← Doit être ici !
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

DATABASES['default']['CONN_MAX_AGE'] = config('DB_CONN_MAX_AGE', default=600, cast=int)
DATABASES['default']['CONN_HEALTH_CHECKS'] = True

"""DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='NSIAPassDB'),
        'USER': config('DB_USER', default='nsia_pass_user'),
        'PASSWORD': config('DB_PASSWORD', default='nsia_pass_password_123'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
    }
}"""

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
    "http://localhost:8081",  # React Native Metro
]
CORS_ALLOW_CREDENTIALS = True

# Internationalization Congo
LANGUAGE_CODE = config('LANGUAGE_CODE', default='fr-fr')
TIME_ZONE = config('TIME_ZONE', default='Africa/Brazzaville')
USE_I18N = True
USE_TZ = True
# =============================================
# FICHIERS STATIQUES (CONFIGURATION CRITIQUE)
# =============================================
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Créer le dossier staticfiles s'il n'existe pas
os.makedirs(STATIC_ROOT, exist_ok=True)

# Configuration Whitenoise pour production
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Répertoires de fichiers statiques
STATICFILES_DIRS = [
    BASE_DIR / 'static',
] if DEBUG else []

# Configuration Whitenoise avancée
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = DEBUG
WHITENOISE_SKIP_COMPRESS_EXTENSIONS = ['jpg', 'jpeg', 'png', 'gif', 'webp']

# =============================================
# MEDIA FILES
# =============================================
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
    'TIMEOUT': 60,
    'BASIC_AUTH_TOKEN': config('MTN_BASIC_AUTH_TOKEN', default=''),
}

# Airtel Money PRODUCTION
AIRTEL_MONEY = {
    'BASE_URL': 'https://openapi.airtel.africa',
    'CLIENT_ID': config('AIRTEL_CLIENT_ID'),
    'CLIENT_SECRET': config('AIRTEL_CLIENT_SECRET'),
    'COUNTRY': 'CG',
    'CURRENCY': 'XAF',
    'TIMEOUT': 60,
}

# Broker et Backend Redis
CELERY_BROKER_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# Sérialisation
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'

# Timezone
CELERY_TIMEZONE = 'Africa/Brazzaville'

# Configuration des tâches périodiques
CELERY_BEAT_SCHEDULE = {
    'monitor-pending-payments': {
        'task': 'apps.pass_payments.tasks.monitor_pending_payments',
        'schedule': 30.0,  # Toutes les 30 secondes
        # Enlever la ligne 'options': {'queue': 'payment_monitoring'}
    },
}

# Et COMMENTER ces lignes pour simplifier :
# CELERY_TASK_ROUTES = {
#     'apps.pass_payments.tasks.*': {'queue': 'payment_monitoring'},
#     'apps.mtn_integration.tasks.*': {'queue': 'mtn_operations'},
#     'apps.airtel_integration.tasks.*': {'queue': 'airtel_operations'},
# }


# Autres configurations Celery
CELERY_TASK_ALWAYS_EAGER = False  # True pour les tests
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_ACKS_LATE = True