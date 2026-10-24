"""Settings for the StudyMate Django API."""

import ssl
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlsplit

import environ
from corsheaders.defaults import default_headers
from django.core.exceptions import ImproperlyConfigured


BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
)
environ.Env.read_env(BASE_DIR / ".env", parse_comments=True)

SECRET_KEY = env("SECRET_KEY")
DEBUG = env.bool("DEBUG", default=False)

_INSECURE_SECRET_VALUES = frozenset(
    {
        "replace-with-a-unique-secret-key",
        "replace-with-a-separate-jwt-signing-key",
        "change-me",
    }
)

if not DEBUG and (len(SECRET_KEY) < 50 or SECRET_KEY in _INSECURE_SECRET_VALUES):
    raise ImproperlyConfigured(
        "Production SECRET_KEY must be a unique, high-entropy environment value."
    )

# Refresh-token revocation is enabled by default only outside local development.
# The blacklist app is part of SimpleJWT; no additional authentication system is
# introduced. It can be explicitly disabled for a controlled deployment if needed.
JWT_TOKEN_BLACKLIST_ENABLED = env.bool(
    "JWT_TOKEN_BLACKLIST_ENABLED", default=not DEBUG
)


def _env_list(name: str) -> list[str]:
    """Read comma-separated environment values without blank/whitespace entries."""

    return [value.strip() for value in env.list(name, default=[]) if value.strip()]


ALLOWED_HOSTS = _env_list("ALLOWED_HOSTS")


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.postgres',
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

if JWT_TOKEN_BLACKLIST_ENABLED:
    INSTALLED_APPS.append('rest_framework_simplejwt.token_blacklist')

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'apps.core.db_observability.SlowQueryLoggingMiddleware',
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

if not DEBUG and DATABASES['default']['ENGINE'] != 'django.db.backends.postgresql':
    raise ImproperlyConfigured('Production DATABASE_URL must use PostgreSQL.')

# Render PostgreSQL supports TLS. Local development keeps the connection
# behavior supplied by DATABASE_URL unless DB_SSLMODE is explicitly set.
DB_SSLMODE = env('DB_SSLMODE', default='require' if not DEBUG else '').strip().lower()
if DB_SSLMODE not in {'', 'disable', 'allow', 'prefer', 'require', 'verify-ca', 'verify-full'}:
    raise ImproperlyConfigured(
        'DB_SSLMODE must be a valid PostgreSQL sslmode value.'
    )
if not DEBUG and DB_SSLMODE not in {'require', 'verify-ca', 'verify-full'}:
    raise ImproperlyConfigured(
        'Production PostgreSQL connections must use DB_SSLMODE=require, verify-ca, or verify-full.'
    )
if DB_SSLMODE:
    # Assign explicitly so a conflicting sslmode query parameter in
    # DATABASE_URL cannot weaken the production requirement.
    DATABASES['default'].setdefault('OPTIONS', {})['sslmode'] = DB_SSLMODE

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

# Request-scoped query timing uses Django's execute-wrapper API. It logs only
# slow-query metadata (duration, SQL verb, request method and route), never SQL
# text or parameters. Debug/local mode stays quiet unless explicitly enabled.
DB_SLOW_QUERY_LOGGING_ENABLED = env.bool(
    'DB_SLOW_QUERY_LOGGING_ENABLED',
    default=not DEBUG,
)
DB_SLOW_QUERY_THRESHOLD_MS = env.float(
    'DB_SLOW_QUERY_THRESHOLD_MS',
    default=250.0,
)
if DB_SLOW_QUERY_THRESHOLD_MS <= 0 or DB_SLOW_QUERY_THRESHOLD_MS > 60000:
    raise ImproperlyConfigured(
        'DB_SLOW_QUERY_THRESHOLD_MS must be greater than 0 and no more than 60000.'
    )


def _build_cache_config(redis_url: str, debug: bool) -> dict:
    """Use shared Redis when configured and fail closed for production."""

    if redis_url:
        if not debug and urlsplit(redis_url).scheme.casefold() != 'rediss':
            raise ImproperlyConfigured(
                'Production REDIS_URL must use the rediss:// TLS scheme.'
            )
        return {
            'default': {
                'BACKEND': 'django_redis.cache.RedisCache',
                'LOCATION': redis_url,
            },
        }
    if not debug:
        raise ImproperlyConfigured(
            'Production cache configuration requires REDIS_URL.'
        )
    return {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'studymate-local-cache',
        },
    }


REDIS_URL = env('REDIS_URL', default='').strip()
CACHES = _build_cache_config(REDIS_URL, DEBUG)

# Celery uses a dedicated setting so the worker can use a separate broker when
# desired. Falling back to REDIS_URL keeps the existing Upstash cache setup
# usable without duplicating a secret in deployment configuration.
CELERY_BROKER_URL = env('CELERY_BROKER_URL', default=REDIS_URL).strip()
if not DEBUG and not CELERY_BROKER_URL:
    raise ImproperlyConfigured(
        'Production Celery configuration requires CELERY_BROKER_URL or REDIS_URL.'
    )
if CELERY_BROKER_URL:
    celery_broker_scheme = urlsplit(CELERY_BROKER_URL).scheme.casefold()
    if celery_broker_scheme not in {'redis', 'rediss'}:
        raise ImproperlyConfigured(
            'CELERY_BROKER_URL must use redis:// or rediss://.'
        )
    if not DEBUG and celery_broker_scheme != 'rediss':
        raise ImproperlyConfigured(
            'Production CELERY_BROKER_URL must use the rediss:// TLS scheme.'
        )
    if celery_broker_scheme == 'rediss':
        CELERY_BROKER_USE_SSL = {'ssl_cert_reqs': ssl.CERT_REQUIRED}

CELERY_TASK_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_IGNORE_RESULT = True
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_DEFAULT_QUEUE = 'celery'
CELERY_TASK_TRACK_STARTED = True
CELERY_WORKER_SEND_TASK_EVENTS = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_TASK_SOFT_TIME_LIMIT = env.int('CELERY_TASK_SOFT_TIME_LIMIT', default=60)
CELERY_TASK_TIME_LIMIT = env.int('CELERY_TASK_TIME_LIMIT', default=120)
if CELERY_TASK_SOFT_TIME_LIMIT <= 0 or CELERY_TASK_TIME_LIMIT <= 0:
    raise ImproperlyConfigured(
        'Celery task time limits must be positive integers.'
    )
if CELERY_TASK_SOFT_TIME_LIMIT >= CELERY_TASK_TIME_LIMIT:
    raise ImproperlyConfigured(
        'CELERY_TASK_SOFT_TIME_LIMIT must be less than CELERY_TASK_TIME_LIMIT.'
    )

# Email backend configuration is environment-driven so the Celery worker and
# web process use the same delivery settings. Tests override EMAIL_BACKEND
# with Django's locmem backend.
EMAIL_BACKEND = env(
    'EMAIL_BACKEND',
    default='django.core.mail.backends.smtp.EmailBackend',
)
EMAIL_HOST = env('EMAIL_HOST', default='')
EMAIL_PORT = env.int('EMAIL_PORT', default=25)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=False)
EMAIL_USE_SSL = env.bool('EMAIL_USE_SSL', default=False)
EMAIL_TIMEOUT = env.int('EMAIL_TIMEOUT', default=10)


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

# Bayesian top-rated ordering uses five ratings as the minimum threshold before
# an item's observed average outweighs the catalogue-wide average.
RESOURCE_RATING_MIN_COUNT = env.int('RESOURCE_RATING_MIN_COUNT', default=5)
if RESOURCE_RATING_MIN_COUNT <= 0:
    raise ImproperlyConfigured('RESOURCE_RATING_MIN_COUNT must be greater than zero.')

SUBJECT_RECOMMENDATION_CACHE_TTL_SECONDS = env.int(
    'SUBJECT_RECOMMENDATION_CACHE_TTL_SECONDS',
    default=600,
)
SUBJECT_RECOMMENDATION_CACHE_TTL_JITTER_SECONDS = env.int(
    'SUBJECT_RECOMMENDATION_CACHE_TTL_JITTER_SECONDS',
    default=30,
)
if not 300 <= SUBJECT_RECOMMENDATION_CACHE_TTL_SECONDS <= 900:
    raise ImproperlyConfigured(
        'SUBJECT_RECOMMENDATION_CACHE_TTL_SECONDS must be between 300 and 900 seconds.'
    )
if (
    SUBJECT_RECOMMENDATION_CACHE_TTL_JITTER_SECONDS < 0
    or SUBJECT_RECOMMENDATION_CACHE_TTL_SECONDS - SUBJECT_RECOMMENDATION_CACHE_TTL_JITTER_SECONDS < 300
    or SUBJECT_RECOMMENDATION_CACHE_TTL_SECONDS + SUBJECT_RECOMMENDATION_CACHE_TTL_JITTER_SECONDS > 900
):
    raise ImproperlyConfigured(
        'SUBJECT_RECOMMENDATION_CACHE_TTL_JITTER_SECONDS must keep the effective TTL between 300 and 900 seconds.'
    )
SUBJECT_RECOMMENDATION_CACHE_VERSION_TTL_SECONDS = env.int(
    'SUBJECT_RECOMMENDATION_CACHE_VERSION_TTL_SECONDS',
    default=1800,
)
if SUBJECT_RECOMMENDATION_CACHE_VERSION_TTL_SECONDS < (
    SUBJECT_RECOMMENDATION_CACHE_TTL_SECONDS
    + SUBJECT_RECOMMENDATION_CACHE_TTL_JITTER_SECONDS
):
    raise ImproperlyConfigured(
        'SUBJECT_RECOMMENDATION_CACHE_VERSION_TTL_SECONDS must be at least the maximum subject cache TTL.'
    )

# Metrics are opt-in because each recorded cache event is an additional cache
# write. The counters are namespace-scoped and retained briefly; they are not
# a substitute for provider-level Redis memory or billing metrics.
CACHE_METRICS_ENABLED = env.bool('CACHE_METRICS_ENABLED', default=False)

PROFILE_AVATAR_MAX_FILE_SIZE_BYTES = env.int('PROFILE_AVATAR_MAX_FILE_SIZE_BYTES', default=5 * 1024 * 1024)
if PROFILE_AVATAR_MAX_FILE_SIZE_BYTES <= 0:
    raise ImproperlyConfigured('PROFILE_AVATAR_MAX_FILE_SIZE_BYTES must be greater than zero.')

# Cloudinary is optional for local development. Credentials are used to
# initialize the SDK and expose named storage aliases.
CLOUDINARY_CLOUD_NAME = env('CLOUDINARY_CLOUD_NAME', default='')
CLOUDINARY_API_KEY = env('CLOUDINARY_API_KEY', default='')
CLOUDINARY_API_SECRET = env('CLOUDINARY_API_SECRET', default='')
CLOUDINARY_CONFIGURED = all(
    (CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET)
)
if not DEBUG and any(
    (CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET)
) and not CLOUDINARY_CONFIGURED:
    raise ImproperlyConfigured(
        'Production Cloudinary configuration requires cloud name, API key, and API secret together.'
    )
if not DEBUG and not CLOUDINARY_CONFIGURED:
    raise ImproperlyConfigured(
        'Production Cloudinary configuration is required for durable media storage.'
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

def _build_storage_config(debug: bool, cloudinary_configured: bool) -> dict:
    default_backend = (
        'django.core.files.storage.FileSystemStorage'
        if debug or not cloudinary_configured
        else 'cloudinary_storage.storage.RawMediaCloudinaryStorage'
    )
    return {
        'default': {
            'BACKEND': default_backend,
        },
        'staticfiles': {
            'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
        },
    }


STORAGES = _build_storage_config(DEBUG, CLOUDINARY_CONFIGURED)

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

# Signup verification uses Django's configured email backend. Deployments can
# provide their normal SMTP/backend settings without changing application code.
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='no-reply@studymate.local')
SIGNUP_OTP_LENGTH = env.int('SIGNUP_OTP_LENGTH', default=6)
SIGNUP_OTP_TTL_SECONDS = env.int('SIGNUP_OTP_TTL_SECONDS', default=600)
SIGNUP_OTP_MAX_ATTEMPTS = env.int('SIGNUP_OTP_MAX_ATTEMPTS', default=5)
SIGNUP_OTP_RESEND_COOLDOWN_SECONDS = env.int(
    'SIGNUP_OTP_RESEND_COOLDOWN_SECONDS', default=60
)
SIGNUP_OTP_EMAIL_RATE_LIMIT = env.int('SIGNUP_OTP_EMAIL_RATE_LIMIT', default=5)
SIGNUP_OTP_EMAIL_RATE_WINDOW_SECONDS = env.int(
    'SIGNUP_OTP_EMAIL_RATE_WINDOW_SECONDS', default=3600
)

# Retention cleanup is deliberately opt-in.  The only currently eligible
# records are completed signup-verification bookkeeping rows; user history,
# notifications, analytics events, and security/audit records are not cleaned
# up by this policy.
RETENTION_CLEANUP_ENABLED = env.bool('RETENTION_CLEANUP_ENABLED', default=False)
SIGNUP_VERIFICATION_CLEANUP_RETENTION_SECONDS = env.int(
    'SIGNUP_VERIFICATION_CLEANUP_RETENTION_SECONDS', default=0
)
RETENTION_CLEANUP_BATCH_SIZE = env.int('RETENTION_CLEANUP_BATCH_SIZE', default=100)
RETENTION_CLEANUP_MAX_BATCHES = env.int('RETENTION_CLEANUP_MAX_BATCHES', default=10)
RETENTION_CLEANUP_BATCH_PAUSE_SECONDS = env.int(
    'RETENTION_CLEANUP_BATCH_PAUSE_SECONDS', default=0
)

if not 4 <= SIGNUP_OTP_LENGTH <= 8:
    raise ImproperlyConfigured('SIGNUP_OTP_LENGTH must be between 4 and 8 digits.')
if SIGNUP_OTP_TTL_SECONDS <= 0 or SIGNUP_OTP_MAX_ATTEMPTS <= 0:
    raise ImproperlyConfigured('Signup OTP expiry and attempt limits must be positive.')
if SIGNUP_OTP_RESEND_COOLDOWN_SECONDS < 0:
    raise ImproperlyConfigured('SIGNUP_OTP_RESEND_COOLDOWN_SECONDS cannot be negative.')
if SIGNUP_OTP_EMAIL_RATE_LIMIT <= 0 or SIGNUP_OTP_EMAIL_RATE_WINDOW_SECONDS <= 0:
    raise ImproperlyConfigured('Signup OTP email rate settings must be positive.')
if SIGNUP_VERIFICATION_CLEANUP_RETENTION_SECONDS < 0:
    raise ImproperlyConfigured(
        'SIGNUP_VERIFICATION_CLEANUP_RETENTION_SECONDS cannot be negative.'
    )
if not 1 <= RETENTION_CLEANUP_BATCH_SIZE <= 1000:
    raise ImproperlyConfigured(
        'RETENTION_CLEANUP_BATCH_SIZE must be between 1 and 1000.'
    )
if not 1 <= RETENTION_CLEANUP_MAX_BATCHES <= 100:
    raise ImproperlyConfigured(
        'RETENTION_CLEANUP_MAX_BATCHES must be between 1 and 100.'
    )
if not 0 <= RETENTION_CLEANUP_BATCH_PAUSE_SECONDS <= 60:
    raise ImproperlyConfigured(
        'RETENTION_CLEANUP_BATCH_PAUSE_SECONDS must be between 0 and 60.'
    )
if (
    RETENTION_CLEANUP_BATCH_PAUSE_SECONDS * RETENTION_CLEANUP_MAX_BATCHES
    >= CELERY_TASK_SOFT_TIME_LIMIT
):
    raise ImproperlyConfigured(
        'Retention cleanup pacing must fit within the Celery soft time limit.'
    )
if RETENTION_CLEANUP_ENABLED and SIGNUP_VERIFICATION_CLEANUP_RETENTION_SECONDS <= 0:
    raise ImproperlyConfigured(
        'Enabled retention cleanup requires an explicit signup-verification retention window.'
    )

# CORS is deliberately limited to the configured frontend origin. Credentials
# are enabled for the HTTP-only-cookie authentication design.
FRONTEND_URL = env('FRONTEND_URL', default='').strip().rstrip('/')
configured_cors_origins = _env_list('CORS_ALLOWED_ORIGINS')
CORS_ALLOWED_ORIGINS = configured_cors_origins or ([FRONTEND_URL] if FRONTEND_URL else [])
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = (*default_headers, "x-upload-id")
CORS_URLS_REGEX = r'^/api/.*$'
configured_csrf_origins = _env_list('CSRF_TRUSTED_ORIGINS')
CSRF_TRUSTED_ORIGINS = configured_csrf_origins or ([FRONTEND_URL] if FRONTEND_URL else [])

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
JWT_COOKIE_SAMESITE = env(
    'JWT_COOKIE_SAMESITE', default='Lax' if DEBUG else 'None'
).strip().capitalize()
JWT_ACCESS_COOKIE_PATH = env('JWT_ACCESS_COOKIE_PATH', default='/')
JWT_REFRESH_COOKIE_PATH = env('JWT_REFRESH_COOKIE_PATH', default='/api/auth/')
JWT_COOKIE_DOMAIN = env('JWT_COOKIE_DOMAIN', default=None)

if JWT_COOKIE_SAMESITE not in {'Lax', 'Strict', 'None'}:
    raise ImproperlyConfigured('JWT_COOKIE_SAMESITE must be Lax, Strict, or None.')

if not DEBUG and (
    not JWT_SIGNING_KEY
    or len(JWT_SIGNING_KEY) < 50
    or JWT_SIGNING_KEY in _INSECURE_SECRET_VALUES
    or JWT_SIGNING_KEY == SECRET_KEY
):
    raise ImproperlyConfigured(
        'Production JWT_SIGNING_KEY must be a separate, unique, high-entropy environment value.'
    )

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=JWT_ACCESS_TOKEN_MINUTES),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=JWT_REFRESH_TOKEN_DAYS),
    'ROTATE_REFRESH_TOKENS': env.bool(
        'JWT_ROTATE_REFRESH_TOKENS', default=JWT_TOKEN_BLACKLIST_ENABLED
    ),
    'BLACKLIST_AFTER_ROTATION': env.bool(
        'JWT_BLACKLIST_AFTER_ROTATION', default=JWT_TOKEN_BLACKLIST_ENABLED
    ),
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
# auth cookies. The CSRF bootstrap endpoint returns the non-secret token for
# cross-origin frontends, which send it in the required X-CSRFToken header.
SESSION_COOKIE_SECURE = env.bool('SESSION_COOKIE_SECURE', default=not DEBUG)
SESSION_COOKIE_SAMESITE = env('SESSION_COOKIE_SAMESITE', default=JWT_COOKIE_SAMESITE)
CSRF_COOKIE_SECURE = env.bool('CSRF_COOKIE_SECURE', default=not DEBUG)
CSRF_COOKIE_SAMESITE = env('CSRF_COOKIE_SAMESITE', default=JWT_COOKIE_SAMESITE)
CSRF_COOKIE_NAME = env('CSRF_COOKIE_NAME', default='csrftoken')
CSRF_COOKIE_PATH = env('CSRF_COOKIE_PATH', default='/')
CSRF_COOKIE_DOMAIN = env('CSRF_COOKIE_DOMAIN', default=None)
CSRF_COOKIE_HTTPONLY = False
CSRF_FAILURE_VIEW = 'apps.core.error_handlers.api_csrf_failure'

if CSRF_COOKIE_SAMESITE not in {'Lax', 'Strict', 'None'}:
    raise ImproperlyConfigured('CSRF_COOKIE_SAMESITE must be Lax, Strict, or None.')

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

LOG_LEVEL = env('LOG_LEVEL', default='INFO').strip().upper()
if LOG_LEVEL not in {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}:
    raise ImproperlyConfigured('LOG_LEVEL must be a standard Python logging level.')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': LOG_LEVEL,
    },
}


def _validate_production_origins() -> None:
    if DEBUG:
        return

    if not ALLOWED_HOSTS or '*' in ALLOWED_HOSTS:
        raise ImproperlyConfigured(
            'Production ALLOWED_HOSTS must contain explicit hostnames and no wildcard.'
        )
    if any(not host or '://' in host or '/' in host for host in ALLOWED_HOSTS):
        raise ImproperlyConfigured(
            'Production ALLOWED_HOSTS values must be hostnames without URL schemes or paths.'
        )
    if not CORS_ALLOWED_ORIGINS:
        raise ImproperlyConfigured(
            'Production CORS_ALLOWED_ORIGINS must explicitly allow the frontend origin.'
        )
    if not FRONTEND_URL:
        raise ImproperlyConfigured(
            'Production FRONTEND_URL must be the exact HTTPS Vercel frontend origin.'
        )
    if not CSRF_TRUSTED_ORIGINS:
        raise ImproperlyConfigured(
            'Production CSRF_TRUSTED_ORIGINS must explicitly trust the frontend origin.'
        )

    frontend = urlsplit(FRONTEND_URL)
    if (
        frontend.scheme != 'https'
        or not frontend.hostname
        or frontend.path not in {'', '/'}
        or frontend.query
        or frontend.fragment
    ):
        raise ImproperlyConfigured(
            'Production FRONTEND_URL must be an explicit HTTPS origin without a path.'
        )

    if {origin.rstrip('/') for origin in CORS_ALLOWED_ORIGINS} != {FRONTEND_URL}:
        raise ImproperlyConfigured(
            'Production CORS_ALLOWED_ORIGINS must contain only FRONTEND_URL.'
        )

    trusted_origins = {trusted.rstrip('/') for trusted in CSRF_TRUSTED_ORIGINS}
    if FRONTEND_URL not in trusted_origins:
        raise ImproperlyConfigured(
            'Production CSRF_TRUSTED_ORIGINS must include FRONTEND_URL.'
        )
    for origin in CORS_ALLOWED_ORIGINS:
        parsed = urlsplit(origin)
        if (
            parsed.scheme != 'https'
            or not parsed.hostname
            or parsed.path not in {'', '/'}
            or parsed.query
            or parsed.fragment
        ):
            raise ImproperlyConfigured(
                'Production CORS_ALLOWED_ORIGINS values must be explicit HTTPS origins.'
            )
        if origin.rstrip('/') not in trusted_origins:
            raise ImproperlyConfigured(
                'Every production CORS origin must also be in CSRF_TRUSTED_ORIGINS.'
            )

    for origin in CSRF_TRUSTED_ORIGINS:
        normalized_origin = origin.replace('https://*.', 'https://placeholder.')
        parsed = urlsplit(normalized_origin)
        if (
            parsed.scheme != 'https'
            or not parsed.hostname
            or parsed.path not in {'', '/'}
            or parsed.query
            or parsed.fragment
        ):
            raise ImproperlyConfigured(
                'Production CSRF_TRUSTED_ORIGINS values must use HTTPS origins.'
            )

    if not JWT_COOKIE_SECURE or not CSRF_COOKIE_SECURE or not SESSION_COOKIE_SECURE:
        raise ImproperlyConfigured(
            'Production authentication, CSRF, and session cookies must be Secure.'
        )
    if JWT_COOKIE_SAMESITE != 'None' or CSRF_COOKIE_SAMESITE != 'None':
        raise ImproperlyConfigured(
            'Production cross-site cookie authentication requires SameSite=None for JWT and CSRF cookies.'
        )
    if not SECURE_SSL_REDIRECT or SECURE_HSTS_SECONDS <= 0:
        raise ImproperlyConfigured(
            'Production must redirect HTTP to HTTPS and enable HSTS.'
        )
    if not SECURE_CONTENT_TYPE_NOSNIFF or X_FRAME_OPTIONS not in {'DENY', 'SAMEORIGIN'}:
        raise ImproperlyConfigured(
            'Production security headers must prevent content-type sniffing and unsafe framing.'
        )


_validate_production_origins()

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
        'auth_signup_verification_request': env(
            'THROTTLE_AUTH_SIGNUP_VERIFICATION_REQUEST_RATE', default='10/hour'
        ),
        'auth_signup_verification_verify': env(
            'THROTTLE_AUTH_SIGNUP_VERIFICATION_VERIFY_RATE', default='30/hour'
        ),
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
    'ENUM_NAME_OVERRIDES': {
        'AcademicLevelTypeEnum': 'apps.education.models.AcademicStageType',
    },
}
