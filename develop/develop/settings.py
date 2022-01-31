"""
Django settings for develop project.

Generated by 'django-admin startproject' using Django 2.2.3.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.2/ref/settings/
"""
import os
from pathlib import Path
import dj_database_url
from iso4217 import Currency

from vendor.__version__ import VERSION
from django.utils.translation import gettext_lazy as _

BUILD_VERSION = VERSION

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = Path(__file__).resolve(strict=True).parent.parent

SITE_ID = int(os.getenv('SITE_ID', '1'))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '&1mmk1e%&9p87fvr=&v84u6fx1)$7f&%)*t9#$zfnu$#h#+5v^'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'core',
    'crispy_forms',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'iso4217',
    'integrations',
    'siteconfigs',
    'vendor'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'develop.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [ os.path.join(BASE_DIR, 'templates') ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.request',
            ],
        },
    },
]

WSGI_APPLICATION = 'develop.wsgi.application'

AUTHENTICATION_BACKENDS = [
    # Needed to login by username in Django admin, regardless of `allauth`
    'django.contrib.auth.backends.ModelBackend',

    # `allauth` specific authentication methods, such as login by e-mail
    'allauth.account.auth_backends.AuthenticationBackend',
]

# Database
# https://docs.djangoproject.com/en/2.2/ref/settings/#databases

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

DATABASES = {}
DATABASES['default'] = dj_database_url.config(conn_max_age=600, ssl_require=False, default=os.environ.get('DATABASE_URL', 'sqlite:///{}'.format(os.path.join(BASE_DIR, 'db.sqlite3'))))     # Default to SQLite for testing on GitHub

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
#     }
# }

# Password validation
# https://docs.djangoproject.com/en/2.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

ACCOUNT_EMAIL_REQUIRED = True

LOGIN_REDIRECT_URL = "/sales/cart/"

FIXTURE_DIRS = (
   os.path.join(BASE_DIR, 'fixtures'),
)

# Internationalization
# https://docs.djangoproject.com/en/2.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.2/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = 'static_root/'

STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static"),
]

# Django Vendor Settings
VENDOR_PRODUCT_MODEL = 'core.Product'
# VENDOR_PAYMENT_PROCESSOR = os.getenv("VENDOR_PAYMENT_PROCESSOR", "base.PaymentProcessorBase")
VENDOR_STATE = os.getenv("VENDOR_STATE", "DEBUG")
VENDOR_CHARGE_VALIDATION_PRICE = os.getenv("VENDOR_CHARGE_VALIDATION_PRICE", 1)
DEFAULT_CURRENCY = Currency.usd.name
AVAILABLE_CURRENCIES = {'usd': _('USD Dollars'), 'mxn': _('Mexican peso'), 'jpy': _('Japanese yen')}

# Authorize.Net Settings:
AUTHORIZE_NET_API_ID = os.getenv("AUTHORIZE_NET_API_ID")
AUTHORIZE_NET_TRANSACTION_KEY = os.getenv("AUTHORIZE_NET_TRANSACTION_KEY")
AUTHORIZE_NET_SIGNATURE_KEY = os.getenv("AUTHORIZE_NET_SIGNATURE_KEY")
AUTHORIZE_NET_KEY = os.getenv("AUTHORIZE_NET_KEY")
AUTHORIZE_NET_TRANSACTION_TYPE_DEFAULT = os.getenv("AUTHORIZE_NET_TRANSACTION_TYPE_DEFAULT")

# Stripe Settings
STRIPE_TEST_SECRET_KEY = os.getenv("STRIPE_TEST_SECRET_KEY")
STRIPE_TEST_PUBLIC_KEY = os.getenv("STRIPE_TEST_PUBLIC_KEY")
STRIPE_LIVE_MODE = False

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

VENDOR_COUNTRY_CHOICE = [
    'US',
    'JP',
    'MX'
]

VENDOR_COUNTRY_DEFAULT = 'US'

#################
# IMPORTANT FOR MIGRATION 0023_profile_null_false
# If you want to set a different User ID as a default for
# Invoice, Receipts, CustomerProfile, and Payments you
# can change the value on MIGRATION_0023_DEFAULT_USER
MIGRATION_0023_DEFAULT_USER = None

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': 'debug.log',
        },
        'console': {
            'level': 'WARNING',
            'class': 'logging.StreamHandler'
        }
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'WARNING',
            'propagate': True,
        },
        'vendor': {
            'handlers': ['file'],
            'level': 'WARNING',
            'propagate': True,
        },
    },
}