"""
Django settings for EduFinApp.

Secrets and environment-specific values are read from environment variables
(or a local, git-ignored `.env` file). See `.env.example` for every option.
The defaults are safe: DEBUG is off unless you turn it on.
"""

import os
import sys
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from django.utils.csp import CSP

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv(path):
    """Load KEY=VALUE lines from a .env file without overriding real env vars."""
    if not path.exists():
        return
    for raw in path.read_text(encoding='utf-8').splitlines():
        line = raw.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key.strip(), value)


_load_dotenv(BASE_DIR / '.env')


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def env_list(name, default=''):
    return [item.strip() for item in os.environ.get(name, default).split(',') if item.strip()]


# --- Core security settings -------------------------------------------------

DEBUG = env_bool('DJANGO_DEBUG', False)

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', '')
if not SECRET_KEY:
    if DEBUG:
        # Development only: a throwaway key so `runserver` works out of the box.
        SECRET_KEY = 'dev-only-insecure-key-change-me'
    else:
        raise ImproperlyConfigured(
            'DJANGO_SECRET_KEY is not set. Copy .env.example to .env and generate a key with:\n'
            '  python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"'
        )

ALLOWED_HOSTS = env_list('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1' if DEBUG else '')
CSRF_TRUSTED_ORIGINS = env_list('DJANGO_CSRF_TRUSTED_ORIGINS')


# --- Applications -----------------------------------------------------------

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'rest_framework',
    'core.apps.CoreConfig',
    'accounts',
    'transaction',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.csp.ContentSecurityPolicyMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.LoginRequiredMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'EduFinApp.urls'

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

WSGI_APPLICATION = 'EduFinApp.wsgi.application'


# --- Database ---------------------------------------------------------------

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.environ.get('DJANGO_DB_PATH', BASE_DIR / 'db.sqlite3'),
    }
}


# --- Authentication ---------------------------------------------------------

AUTH_USER_MODEL = 'accounts.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 10}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'


# --- Cookies, HTTPS and headers --------------------------------------------
# Secure-by-default when DEBUG is off; each can be overridden from the environment
# (for example when running the production settings locally without HTTPS).

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 60 * 60 * 8  # 8 hours
SESSION_COOKIE_SECURE = env_bool('DJANGO_SECURE_COOKIES', not DEBUG)
CSRF_COOKIE_SECURE = env_bool('DJANGO_SECURE_COOKIES', not DEBUG)
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'

SECURE_SSL_REDIRECT = env_bool('DJANGO_SECURE_SSL_REDIRECT', not DEBUG)
SECURE_HSTS_SECONDS = int(os.environ.get('DJANGO_HSTS_SECONDS', '0' if DEBUG else '31536000'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool('DJANGO_HSTS_INCLUDE_SUBDOMAINS', not DEBUG)
SECURE_HSTS_PRELOAD = env_bool('DJANGO_HSTS_PRELOAD', False)
if env_bool('DJANGO_BEHIND_PROXY', False):
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin'
X_FRAME_OPTIONS = 'DENY'

# Strict Content Security Policy (Django 6 built-in): no inline scripts or styles.
SECURE_CSP = {
    'default-src': [CSP.SELF],
    'script-src': [CSP.SELF],
    'style-src': [CSP.SELF],
    'img-src': [CSP.SELF, 'data:'],
    'font-src': [CSP.SELF],
    'connect-src': [CSP.SELF],
    'object-src': [CSP.NONE],
    'base-uri': [CSP.SELF],
    'form-action': [CSP.SELF],
    'frame-ancestors': [CSP.NONE],
}


# --- Django REST Framework --------------------------------------------------

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
}


# --- Internationalisation ---------------------------------------------------

LANGUAGE_CODE = 'en-us'
TIME_ZONE = os.environ.get('DJANGO_TIME_ZONE', 'Africa/Kigali')
USE_I18N = True
USE_TZ = True

# Currency shown in the UI (Rwandan franc by default).
CURRENCY = os.environ.get('EDUFIN_CURRENCY', 'RWF')


# --- Static files -----------------------------------------------------------

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# --- Logging: record security-relevant events -------------------------------

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {'plain': {'format': '{asctime} {levelname} {name} {message}', 'style': '{'}},
    'handlers': {'console': {'class': 'logging.StreamHandler', 'formatter': 'plain'}},
    'loggers': {
        'django.security': {'handlers': ['console'], 'level': 'WARNING'},
        'edufin.security': {'handlers': ['console'], 'level': 'INFO'},
    },
}
if len(sys.argv) > 1 and sys.argv[1] == 'test':
    # Keep test output readable; the audit trail is still written to the database.
    LOGGING['loggers']['edufin.security']['level'] = 'WARNING'
    LOGGING['loggers']['django.security']['level'] = 'ERROR'
