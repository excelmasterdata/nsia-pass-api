import os
from pathlib import Path
from decouple import config
from datetime import timedelta

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent

# =============================================
# SÉCURITÉ PRODUCTION
# =============================================
SECRET_KEY = config('SECRET_KEY', default='nsia-pass-django-secret-key-congo-2024')
DEBUG = config('DEBUG', default=False, cast=bool)  # ← FALSE en production !

# ALLOWED_HOSTS pour Render + local
ALLOWED_HOSTS = [
    'localhost', 
    '127.0.0.1', 
    '.onrender.com',  # ← Pour tous les sous-domaines Render
    'nsia-pass-api.onrender.com'  # ← Votre URL exacte
]

# =============================================
# APPLICATIONS NSIA PASS
# =============================================
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

# =============================================
# MIDDLEWARE (ORDRE CRITIQUE POUR WHITENOISE)
# =============================================
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # ← POSITION CRITIQUE !
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'nsia_pass_api.urls'

# =============================================
# TEMPLATES
# =============================================
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

# =============================================
# BASE DE DONNÉES NSIA DISTANTE
# =============================================
def parse_database_url(url):
    """Parse DATABASE_URL manuellement"""
    if not url or not url.startswith('postgresql://'):
        return None
    
    import re
    match = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', url)
    
    if match:
        user, password, host, port, dbname = match.groups()
        return {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': dbname,
            'USER': user,
            'PASSWORD': password,
            'HOST': host,
            'PORT': port,
            'OPTIONS': {
                'sslmode': 'require',
                'connect_timeout': 30,
            },
        }
    return None

# Configuration base de données
database_url = config('DATABASE_URL', default=None)
parsed_db = parse_database_url(database_url)

if parsed_db:
    DATABASES = {'default': parsed_db}
else:
    # Développement local
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

# =============================================
# VALIDATION MOTS DE PASSE
# =============================================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# =============================================
# REST FRAMEWORK NSIA PASS
# =============================================
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

# =============================================
# JWT POUR BORNE INTERACTIVE
# =============================================
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),  # Session borne courte
    'REFRESH_TOKEN_LIFETIME': timedelta(hours=1),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}

# =============================================
# CORS POUR BORNE REACT NATIVE
# =============================================
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8081",  # React Native Metro
    "https://nsia-pass-api.onrender.com",  # Votre API
]
CORS_ALLOW_CREDENTIALS = True

# =============================================
# INTERNATIONALISATION CONGO
# =============================================
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Brazzaville'
USE_I18N = True
USE_TZ = True

# =============================================
# MTN MOBILE MONEY CONGO
# =============================================
MTN_MOBILE_MONEY = {
    'BASE_URL': config('MTN_API_BASE_URL', default='https://sandbox.momodeveloper.mtn.com'),
    'COLLECTION_USER_ID': config('MTN_COLLECTION_USER_ID', default=''),
    'COLLECTION_API_KEY': config('MTN_COLLECTION_API_KEY', default=''),
    'COLLECTION_SUBSCRIPTION_KEY': config('MTN_COLLECTION_SUBSCRIPTION_KEY', default=''),
    'ENVIRONMENT': config('MTN_ENVIRONMENT', default='sandbox'),
    'CURRENCY': 'XAF',  # Franc CFA Congo
    'COUNTRY': 'CG',    # Congo-Brazzaville
}

# =============================================
# SÉCURITÉ PRODUCTION
# =============================================
if not DEBUG:
    # HTTPS obligatoire en production
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# =============================================
# CONFIGURATION FINALE
# =============================================
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Force collectstatic en production si nécessaire
if not DEBUG and not os.listdir(STATIC_ROOT):
    import subprocess
    try:
        subprocess.run(['python', 'manage.py', 'collectstatic', '--no-input'], check=True)
    except:
        pass

# =============================================
# LOGGING POUR DEBUG
# =============================================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'whitenoise': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
        },
    },
}