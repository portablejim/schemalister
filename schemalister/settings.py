import os
import environ
from pathlib import Path
import sys
from urllib.parse import urlsplit

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    ENVIRONMENT=(str, 'production'),
    DEBUG=(bool, False),
    REDIS_URL=(str, 'redis://localhost:6379'),
    SALESFORCE_CONSUMER_KEY=(str, ''),
    SALESFORCE_CONSUMER_SECRET=(str, ''),
    SALESFORCE_API_VERSION=(int, 65),
    SALESFORCE_REDIRECT_URI=(str, ''),
    PGDATABASE=(str, None),
    PGUSER=(str, None),
    PGPASSWORD=(str, None),
    PGHOST=(str, None),
    PGPORT=(str, None),
    LANGUAGE_CODE=(str, 'en-au'),
    TIME_ZONE=(str, 'Australia/Sydney'),
    EXTERNAL_APP_PACKAGEID_PRODUCTION=(str, None),
    EXTERNAL_APP_PACKAGEID_SANDBOX=(str, None),
)
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

ENVIRONMENT = env('ENVIRONMENT')
IS_LOCAL = ENVIRONMENT == 'dev'

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("DJANGO_SECRET_KEY")
SECRETS_ENCRYPTION_KEY = env("SECRETS_ENCRYPTION_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True if IS_LOCAL else bool(env('DEBUG'))

if not IS_LOCAL:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True
    CSRF_TRUSTED_ORIGINS = [
        'https://schemalister.cloudtoolkit.co'
    ]

ADMINS = (
    ('Ben Edwards', 'ben@edwards.nz'),
)

ALLOWED_HOSTS = ['*']

# Application definition

INSTALLED_APPS = [
    'whitenoise.runserver_nostatic',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'getschema',
    'django_celery_beat',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    "whitenoise.middleware.WhiteNoiseMiddleware",
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'schemalister.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'templates'
        ],
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

WSGI_APPLICATION = 'schemalister.wsgi.application'

MAX_CONN_AGE = 600

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': env('REDIS_URL'),
        'KEY_PREFIX': 'django-',
        'OPTIONS': {
            'TIMEOUT': 3600
        }
    }
}

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

ENABLE_POSTGRES = False
if 'DATABASE_URL' in env and env('DATABASE_URL') is not None and len(env('DATABASE_URL')) > 0:
    parsed_db_url = urlsplit(env('DATABASE_URL'))
    if parsed_db_url.scheme == 'postgres':
        ENABLE_POSTGRES = True
        env["PGDATABASE"] = parsed_db_url.path[1:]
        env["PGUSER"] = parsed_db_url.username
        env["PGPASSWORD"] = parsed_db_url.password
        env["PGHOST"] = parsed_db_url.hostname
        env["PGPORT"] = parsed_db_url.port
    if parsed_db_url.scheme == 'sqlite':
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': BASE_DIR / parsed_db_url.path,
            }
        }



# For running on server
if not IS_LOCAL or ENABLE_POSTGRES:
    # Configure Django for DATABASE_URL environment variable.
    DATABASES["default"] = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env("PGDATABASE"),
        'USER': env("PGUSER"),
        'PASSWORD': env("PGPASSWORD"),
        'HOST': env("PGHOST"),
        'PORT': env("PGPORT"),
    }

STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Celery settings
REDIS_URL = env('REDIS_URL')
CELERY_BROKER_URL = REDIS_URL
BROKER_POOL_LIMIT = 1
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/
LANGUAGE_CODE = env('LANGUAGE_CODE')
TIME_ZONE = env('TIME_ZONE')
USE_I18N = True
USE_TZ = True


STATIC_ROOT = BASE_DIR / "staticfiles"
STATIC_URL = "static/"

STATICFILES_DIRS = [
    BASE_DIR / 'static'
]

SALESFORCE_CONSUMER_KEY = env('SALESFORCE_CONSUMER_KEY')
SALESFORCE_CONSUMER_SECRET = env('SALESFORCE_CONSUMER_SECRET')
SALESFORCE_REDIRECT_URI = env('SALESFORCE_REDIRECT_URI')
SALESFORCE_API_VERSION = int(env('SALESFORCE_API_VERSION'))

EXTERNAL_APP_PACKAGEID_PRODUCTION=env('EXTERNAL_APP_PACKAGEID_PRODUCTION')
EXTERNAL_APP_PACKAGEID_SANDBOX=env('EXTERNAL_APP_PACKAGEID_SANDBOX')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False, # Retain Django's default loggers
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'stream': sys.stdout, # Explicitly direct to stdout
            'formatter': 'simple',
        },
    },
    'loggers': {
        '': { # This is the "root" logger, handling all messages by default
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.request': { # Django's request logger
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
