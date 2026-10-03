"""Settings for the StudyMate Django API."""

from datetime import timedelta
from pathlib import Path

import environ
from django.core.exceptions import ImproperlyConfigured


BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
)
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")


def _env_list(name: str) -> list[str]:
    """Read comma-separated environment values without blank/whitespace entries."""

    return [value.strip() for value in env.list(name, default=[]) if value.strip()]


ALLOWED_HOSTS = _env_list("ALLOWED_HOSTS")


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'cloudinary_storage',
    'cloudinary',
    'corsheaders',
    'rest_framework',
    'drf_spectacular',
    'apps.core',
    'apps.users',
    'apps.education',
    'apps.resources',
    'apps.community',
    'apps.interactions',
    'apps.notifications',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'backend.wsgi.application'


DATABASES = {
    'default': env.db('DATABASE_URL'),
}

# A persistent connection is owned by each request-serving thread. The
# threaded development server can therefore create one PostgreSQL session
# per visited request when CONN_MAX_AGE is non-zero, eventually exhausting a
# small local PostgreSQL instance. Keep the safe no-pooling default for local
# and production deployments; an explicitly bounded value can be supplied
# when the deployment's worker/thread budget and PostgreSQL capacity justify
# it.
DB_CONN_MAX_AGE = env.int('DB_CONN_MAX_AGE', default=0)
if DB_CONN_MAX_AGE < 0:
    raise ImproperlyConfigured('DB_CONN_MAX_AGE must not be negative.')
DATABASES['default']['CONN_MAX_AGE'] = DB_CONN_MAX_AGE
DATABASES['default']['CONN_HEALTH_CHECKS'] = env.bool('DB_CONN_HEALTH_CHECKS', default=True)


# Password validation
# https://docs.djangoproject.com/en/6.1/ref/settings/#auth-password-validators

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


LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

RESOURCE_MAX_FILE_SIZE_BYTES = env.int('RESOURCE_MAX_FILE_SIZE_BYTES', default=20 * 1024 * 1024)
if RESOURCE_MAX_FILE_SIZE_BYTES <= 0:
    raise ImproperlyConfigured('RESOURCE_MAX_FILE_SIZE_BYTES must be greater than zero.')

PROFILE_AVATAR_MAX_FILE_SIZE_BYTES = env.int('PROFILE_AVATAR_MAX_FILE_SIZE_BYTES', default=5 * 1024 * 1024)
if PROFILE_AVATAR_MAX_FILE_SIZE_BYTES <= 0:
    raise ImproperlyConfigured('PROFILE_AVATAR_MAX_FILE_SIZE_BYTES must be greater than zero.')

# Cloudinary is optional for local development. Credentials are only used to
# initialize the SDK and expose a named storage alias; existing local and
# legacy file behavior remains on Django's default filesystem storage.
CLOUDINARY_CLOUD_NAME = env('CLOUDINARY_CLOUD_NAME', default='')
CLOUDINARY_API_KEY = env('CLOUDINARY_API_KEY', default='')
CLOUDINARY_API_SECRET = env('CLOUDINARY_API_SECRET', default='')
CLOUDINARY_CONFIGURED = all(
    (CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET)
)
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': CLOUDINARY_CLOUD_NAME,
    'API_KEY': CLOUDINARY_API_KEY,
    'API_SECRET': CLOUDINARY_API_SECRET,
    'SECURE': True,
    'PREFIX': '',
}
CLOUDINARY_RESOURCE_FOLDER = env('CLOUDINARY_RESOURCE_FOLDER', default='studymate/resources').strip('/')
CLOUDINARY_AVATAR_FOLDER = env('CLOUDINARY_AVATAR_FOLDER', default='studymate/avatars').strip('/')

# Keep the current Django storage behavior explicit and provide Cloudinary as
# an opt-in alias for a future resource-file storage migration.
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
    },
}

if CLOUDINARY_CONFIGURED:
    import cloudinary

    cloudinary.config(
        cloud_name=CLOUDINARY_CLOUD_NAME,
        api_key=CLOUDINARY_API_KEY,
        api_secret=CLOUDINARY_API_SECRET,
        secure=True,
    )
    STORAGES['cloudinary_media'] = {
        'BACKEND': 'cloudinary_storage.storage.RawMediaCloudinaryStorage',
    }
    STORAGES['cloudinary_images'] = {
        'BACKEND': 'cloudinary_storage.storage.MediaCloudinaryStorage',
    }

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CORS is deliberately limited to configured frontend origins. Credentials are
# enabled now so the future HTTP-only-cookie authentication design is supported.
CORS_ALLOWED_ORIGINS = _env_list('CORS_ALLOWED_ORIGINS')
CORS_ALLOW_CREDENTIALS = True
CORS_URLS_REGEX = r'^/api/.*$'
CSRF_TRUSTED_ORIGINS = _env_list('CSRF_TRUSTED_ORIGINS')

# JWT/cookie authentication settings. Secrets remain environment-controlled;
# the Django SECRET_KEY is only the safe local fallback when a separate JWT
# signing key has not been supplied.
JWT_SIGNING_KEY = env('JWT_SIGNING_KEY', default=SECRET_KEY)
JWT_ACCESS_TOKEN_MINUTES = env.int('JWT_ACCESS_TOKEN_MINUTES', default=15)
JWT_REFRESH_TOKEN_DAYS = env.int('JWT_REFRESH_TOKEN_DAYS', default=7)
JWT_ACCESS_COOKIE_NAME = env('JWT_ACCESS_COOKIE_NAME', default='studymate_access')
JWT_REFRESH_COOKIE_NAME = env('JWT_REFRESH_COOKIE_NAME', default='studymate_refresh')
JWT_COOKIE_HTTPONLY = True
JWT_ACCESS_COOKIE_HTTPONLY = True
JWT_REFRESH_COOKIE_HTTPONLY = True
JWT_COOKIE_SECURE = env.bool('JWT_COOKIE_SECURE', default=not DEBUG)
JWT_COOKIE_SAMESITE = env('JWT_COOKIE_SAMESITE', default='Lax')
JWT_ACCESS_COOKIE_PATH = env('JWT_ACCESS_COOKIE_PATH', default='/')
JWT_REFRESH_COOKIE_PATH = env('JWT_REFRESH_COOKIE_PATH', default='/api/auth/')
JWT_COOKIE_DOMAIN = env('JWT_COOKIE_DOMAIN', default=None)

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=JWT_ACCESS_TOKEN_MINUTES),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=JWT_REFRESH_TOKEN_DAYS),
    'ROTATE_REFRESH_TOKENS': env.bool('JWT_ROTATE_REFRESH_TOKENS', default=False),
    'BLACKLIST_AFTER_ROTATION': env.bool('JWT_BLACKLIST_AFTER_ROTATION', default=False),
    'UPDATE_LAST_LOGIN': env.bool('JWT_UPDATE_LAST_LOGIN', default=False),
    'ALGORITHM': env('JWT_ALGORITHM', default='HS256'),
    'SIGNING_KEY': JWT_SIGNING_KEY,
    'VERIFYING_KEY': env('JWT_VERIFYING_KEY', default=''),
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

# Session/CSRF cookies follow the same local-vs-production secure default as
# auth cookies. CSRF remains readable by the frontend so it can send the
# required X-CSRFToken header for unsafe cookie-authenticated requests.
SESSION_COOKIE_SECURE = env.bool('SESSION_COOKIE_SECURE', default=not DEBUG)
SESSION_COOKIE_SAMESITE = env('SESSION_COOKIE_SAMESITE', default=JWT_COOKIE_SAMESITE)
CSRF_COOKIE_SECURE = env.bool('CSRF_COOKIE_SECURE', default=not DEBUG)
CSRF_COOKIE_SAMESITE = env('CSRF_COOKIE_SAMESITE', default=JWT_COOKIE_SAMESITE)
CSRF_COOKIE_HTTPONLY = False
CSRF_FAILURE_VIEW = 'apps.core.error_handlers.api_csrf_failure'

# Explicit response-header defaults protect production while remaining harmless
# for local HTTP development. Each value can be changed through the environment.
X_FRAME_OPTIONS = env('X_FRAME_OPTIONS', default='DENY')
SECURE_CONTENT_TYPE_NOSNIFF = env.bool('SECURE_CONTENT_TYPE_NOSNIFF', default=not DEBUG)
SECURE_REFERRER_POLICY = env('SECURE_REFERRER_POLICY', default='same-origin')
SECURE_CROSS_ORIGIN_OPENER_POLICY = env(
    'SECURE_CROSS_ORIGIN_OPENER_POLICY', default='same-origin'
)

# Render and other reverse proxies pass the original request scheme in this
# header. Redirects and HSTS are enabled only for non-debug deployments, so
# local HTTP development remains usable even if production values are present
# in a shared environment configuration.
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', default=True)
    SECURE_HSTS_SECONDS = env.int('SECURE_HSTS_SECONDS', default=31536000)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool('SECURE_HSTS_INCLUDE_SUBDOMAINS', default=True)
    SECURE_HSTS_PRELOAD = env.bool('SECURE_HSTS_PRELOAD', default=False)
else:
    SECURE_SSL_REDIRECT = False
    SECURE_HSTS_SECONDS = 0
    SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    SECURE_HSTS_PRELOAD = False

if SECURE_HSTS_SECONDS < 0:
    raise ImproperlyConfigured('SECURE_HSTS_SECONDS must not be negative.')

# New API endpoints are private by default. The public health endpoint opts out
# explicitly while authentication is introduced in a later milestone.
REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'apps.core.authentication.CookieJWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'apps.core.pagination.StudyMatePagination',
    'EXCEPTION_HANDLER': 'apps.core.exceptions.api_exception_handler',
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
        'rest_framework.throttling.ScopedRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        # Broad defaults keep normal browsing and authenticated API use usable.
        'anon': env('THROTTLE_ANON_RATE', default='300/hour'),
        'user': env('THROTTLE_USER_RATE', default='1200/hour'),
        # Narrower buckets protect state-changing and authentication endpoints.
        'auth_login': env('THROTTLE_AUTH_LOGIN_RATE', default='30/minute'),
        'auth_signup': env('THROTTLE_AUTH_SIGNUP_RATE', default='20/hour'),
        'auth_refresh': env('THROTTLE_AUTH_REFRESH_RATE', default='60/minute'),
        'resource_write': env('THROTTLE_RESOURCE_WRITE_RATE', default='60/hour'),
        'question_write': env('THROTTLE_QUESTION_WRITE_RATE', default='60/hour'),
        'answer_write': env('THROTTLE_ANSWER_WRITE_RATE', default='120/hour'),
        'interaction_write': env('THROTTLE_INTERACTION_WRITE_RATE', default='300/minute'),
        'onboarding_write': env('THROTTLE_ONBOARDING_WRITE_RATE', default='60/hour'),
        'event_write': env('THROTTLE_EVENT_WRITE_RATE', default='300/minute'),
    },
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'StudyMate API',
    'DESCRIPTION': 'OpenAPI documentation for the StudyMate API.',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
}
