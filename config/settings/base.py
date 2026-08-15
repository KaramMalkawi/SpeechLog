import os
from pathlib import Path

import environ
from corsheaders.defaults import default_headers

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DJANGO_ENV=(str, "local"),
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
    SECRET_KEY=(str, ""),
    DATABASE_URL=(str, "postgres://mixed_miles:mixed_miles@localhost:5432/mixed_miles"),
    DATABASE_REPLICA_ENABLED=(bool, False),
    DATABASE_REPLICA_URL=(str, ""),
    REDIS_URL=(str, "redis://localhost:6379/0"),
    CELERY_BROKER_URL=(str, ""),
    CELERY_RESULT_BACKEND=(str, ""),
    CORS_ALLOWED_ORIGINS=(list, []),
    DIDIT_API_KEY=(str, ""),
    DIDIT_WORKFLOW_ID=(str, ""),
    DIDIT_WEBHOOK_SECRET=(str, ""),
    DIDIT_API_BASE_URL=(str, "https://verification.didit.me"),
    DIDIT_CALLBACK_URL=(str, ""),
    VERIFY_TEST_PAGE_ENABLED=(bool, False),
    RESEND_API_KEY=(str, ""),
    RESEND_FROM_EMAIL=(str, "Mixed Miles <hello@mixedmiles.com>"),
    EMAIL_BRAND_LOGO_URL=(str, ""),
    PASSWORD_RESET_FRONTEND_URL=(str, "https://mixedmiles.com/reset-password"),
    ADMIN_DASHBOARD_URL=(str, "https://admin.mixedmiles.com"),
    AWS_S3_ACCESS_KEY_ID=(str, ""),
    AWS_S3_SECRET_ACCESS_KEY=(str, ""),
    AWS_STORAGE_BUCKET_NAME=(str, ""),
    AWS_S3_REGION_NAME=(str, "eu-west-1"),
    AWS_S3_ENDPOINT_URL=(str, ""),
    AWS_S3_PUBLIC_ENDPOINT_URL=(str, ""),
    MEDIA_CDN_BASE_URL=(str, ""),
    GOOGLE_SA_PROJECT_ID=(str, ""),
    GOOGLE_SA_PRIVATE_KEY_ID=(str, ""),
    GOOGLE_SA_PRIVATE_KEY=(str, ""),
    GOOGLE_SA_CLIENT_EMAIL=(str, ""),
    GOOGLE_SA_CLIENT_ID=(str, ""),
    FOUNDER_APPLICATIONS_SHEET_NAME=(
        str,
        "mixed_miles_city_founder_application (Responses)",
    ),
    FOUNDER_APPLICATIONS_SHEET_ID=(str, ""),
)

environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY") or "insecure-dev-only-change-me"
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "drf_spectacular",
    "core.apps.CoreConfig",
    "apps.tenancy.apps.TenancyConfig",
    "apps.accounts.apps.AccountsConfig",
    "apps.founders.apps.FoundersConfig",
    "apps.adminpanel.apps.AdminPanelConfig",
    "apps.notifications.apps.NotificationsConfig",
    "apps.events.apps.EventsConfig",
    "apps.trust_voting.apps.TrustVotingConfig",
    "apps.gatherings.apps.GatheringsConfig",
    "apps.feed.apps.FeedConfig",
    "apps.guidebook.apps.GuidebookConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "core.middleware.TenantMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": env.db("DATABASE_URL"),
}

DATABASE_REPLICA_ENABLED = env("DATABASE_REPLICA_ENABLED")
DATABASE_REPLICA_URL = env("DATABASE_REPLICA_URL")

if DATABASE_REPLICA_ENABLED:
    if not DATABASE_REPLICA_URL:
        raise ValueError("DATABASE_REPLICA_URL must be set when DATABASE_REPLICA_ENABLED is True")
    DATABASES["replica"] = env.db("DATABASE_REPLICA_URL")
    DATABASE_ROUTERS = ["core.db_router.ReadReplicaRouter"]
else:
    DATABASE_ROUTERS = []

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTH_USER_MODEL = "accounts.User"

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REDIS_URL = env("REDIS_URL")

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    }
}

SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

CELERY_BROKER_URL = env("CELERY_BROKER_URL") or REDIS_URL
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND") or REDIS_URL
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60

from celery.schedules import crontab
from datetime import timedelta

# Sync Google Form responses twice daily (UTC) to stay within Sheets API quotas.
# Manual refresh is also available via the admin Applications page.
CELERY_BEAT_SCHEDULE = {
    "sync-founder-applications-1200-utc": {
        "task": "apps.founders.tasks.sync_founder_applications_task",
        "schedule": crontab(hour=12, minute=0),
    },
    "sync-founder-applications-1800-utc": {
        "task": "apps.founders.tasks.sync_founder_applications_task",
        "schedule": crontab(hour=18, minute=0),
    },
    # Trust voting background jobs
    "trust-voting-create-windows": {
        "task": "apps.trust_voting.tasks.create_voting_windows_and_send_prompts",
        # run every 15 minutes to pick up recently-ended events
        "schedule": crontab(minute='*/15'),
    },
    "trust-voting-close-windows": {
        "task": "apps.trust_voting.tasks.close_expired_voting_windows",
        # run every 10 minutes to close windows promptly
        "schedule": crontab(minute='*/10'),
    },
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.accounts.authentication.VerifiedJWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
        "apps.accounts.permissions.IsIdentityVerified",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.CursorPagination",
    "PAGE_SIZE": 20,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Mixed Miles API",
    "DESCRIPTION": "Mixed Miles backend API",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": r"/api/v1/",
    "COMPONENT_SPLIT_REQUEST": True,
    "TAGS": [
        {"name": "system", "description": "Platform health and ops"},
        {"name": "accounts", "description": "Users and memberships"},
        {"name": "founders", "description": "City Founder profiles and admin management"},
        {"name": "tenancy", "description": "Cities and communities"},
        {"name": "events", "description": "Community events, tickets, and join requests"},
        {"name": "trust_voting", "description": "Post-event founder trust voting and scoring"},
        {"name": "gatherings", "description": "Member gatherings with hard-cap attendance"},
    ],
}

API_DOCS_ENABLED = env.bool("API_DOCS_ENABLED", default=False)

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": False,
    "UPDATE_LAST_LOGIN": True,
}

REGISTRATION_TOKEN_LIFETIME = timedelta(hours=24)

DIDIT_API_KEY = env("DIDIT_API_KEY")
DIDIT_WORKFLOW_ID = env("DIDIT_WORKFLOW_ID")
DIDIT_WEBHOOK_SECRET = env("DIDIT_WEBHOOK_SECRET")
DIDIT_API_BASE_URL = env("DIDIT_API_BASE_URL")
DIDIT_CALLBACK_URL = env("DIDIT_CALLBACK_URL")
VERIFY_TEST_PAGE_ENABLED = env("VERIFY_TEST_PAGE_ENABLED")

# Email (Resend)
RESEND_API_KEY = env("RESEND_API_KEY")
RESEND_FROM_EMAIL = env("RESEND_FROM_EMAIL")
EMAIL_BRAND_NAME = "Mixed Miles"
EMAIL_BRAND_WEBSITE = "https://mixedmiles.com/"
ADMIN_DASHBOARD_URL = env("ADMIN_DASHBOARD_URL", default="https://admin.mixedmiles.com")
EMAIL_BRAND_LOGO_URL = env(
    "EMAIL_BRAND_LOGO_URL",
    default="https://mixedmiles.com/assets/mixed-miles-logo-CPWQdpDb.png",
)
EMAIL_SUPPORT_EMAIL = "albara@mixedmiles.com"
EMAIL_SUPPORT_PHONE = "+962 79 797 7255"
EMAIL_SUPPORT_LOCATION = "Amman, Jordan"
EMAIL_BRAND_COLORS = {
    "primary": "#933278",
    "accent": "#E7B220",
    "background": "#FFFFFF",
    "text": "#1A1A1A",
    "muted": "#6B7280",
    "border": "#E5E7EB",
    "header_bg": "#FFFFFF",
}
PASSWORD_RESET_TIMEOUT = 60 * 60
PASSWORD_RESET_FRONTEND_URL = env("PASSWORD_RESET_FRONTEND_URL")
PASSWORD_RESET_EMAIL_RATE_LIMIT = 3
PASSWORD_RESET_IP_RATE_LIMIT = 10
PASSWORD_RESET_RATE_LIMIT_PERIOD = 60 * 60

# Email OTP verification (registration). OTP is hashed with Argon2 before Redis storage.
EMAIL_OTP_LENGTH = 6
EMAIL_OTP_TIMEOUT = 10 * 60
EMAIL_OTP_MAX_ATTEMPTS = 5
EMAIL_OTP_EMAIL_RATE_LIMIT = 5
EMAIL_OTP_IP_RATE_LIMIT = 20
EMAIL_OTP_RATE_LIMIT_PERIOD = 60 * 60

AWS_S3_ACCESS_KEY_ID = env("AWS_S3_ACCESS_KEY_ID")
AWS_S3_SECRET_ACCESS_KEY = env("AWS_S3_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME")
AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME")
AWS_S3_ENDPOINT_URL = env("AWS_S3_ENDPOINT_URL")
AWS_S3_PUBLIC_ENDPOINT_URL = env("AWS_S3_PUBLIC_ENDPOINT_URL")
MEDIA_CDN_BASE_URL = env("MEDIA_CDN_BASE_URL")

# Google Sheets (City Founder application form responses). Prefer SHEET_ID
# (from the spreadsheet URL) so only the Sheets API is required; NAME needs Drive API.
GOOGLE_SA_PROJECT_ID = env("GOOGLE_SA_PROJECT_ID")
GOOGLE_SA_PRIVATE_KEY_ID = env("GOOGLE_SA_PRIVATE_KEY_ID")
GOOGLE_SA_PRIVATE_KEY = env("GOOGLE_SA_PRIVATE_KEY")
GOOGLE_SA_CLIENT_EMAIL = env("GOOGLE_SA_CLIENT_EMAIL")
GOOGLE_SA_CLIENT_ID = env("GOOGLE_SA_CLIENT_ID")
FOUNDER_APPLICATIONS_SHEET_NAME = env("FOUNDER_APPLICATIONS_SHEET_NAME")
FOUNDER_APPLICATIONS_SHEET_ID = env("FOUNDER_APPLICATIONS_SHEET_ID")

PROFILE_PHOTO_KEY_PREFIX = "profile-photos"
PROFILE_PHOTO_MAX_BYTES = 5 * 1024 * 1024
PROFILE_PHOTO_PRESIGNED_EXPIRY = 15 * 60
PROFILE_PHOTO_ALLOWED_CONTENT_TYPES = (
    "image/jpeg",
    "image/png",
    "image/webp",
)

EVENT_COVER_KEY_PREFIX = "event-covers"
EVENT_COVER_MAX_BYTES = 8 * 1024 * 1024
EVENT_COVER_PRESIGNED_EXPIRY = 15 * 60
EVENT_COVER_ALLOWED_CONTENT_TYPES = (
    "image/jpeg",
    "image/png",
    "image/webp",
)
EVENT_ATTENDEE_PREVIEW_LIMIT = 4
DEFAULT_EVENT_CURRENCY = "JOD"

GATHERING_COVER_KEY_PREFIX = "gathering-covers"
GATHERING_COVER_MAX_BYTES = 8 * 1024 * 1024
GATHERING_COVER_PRESIGNED_EXPIRY = 15 * 60
GATHERING_COVER_ALLOWED_CONTENT_TYPES = (
    "image/jpeg",
    "image/png",
    "image/webp",
)

PARTNER_IMAGE_KEY_PREFIX = "partner-images"
PARTNER_IMAGE_MAX_BYTES = 8 * 1024 * 1024
PARTNER_IMAGE_ALLOWED_CONTENT_TYPES = (
    "image/jpeg",
    "image/png",
    "image/webp",
)

# ISO 3166-1 alpha-2 codes where users may register as residents.
RESIDENCE_COUNTRY_CODES = ["JO"]

# Home community assigned when a user has no active_community_id yet.
# Matches the seeded Amman Expats community used for local mobile testing.
DEFAULT_COMMUNITY_SLUG = env("DEFAULT_COMMUNITY_SLUG", default="amman-expats")

# Minimum age (years) required from ID document date_of_birth to verify an account.
MIN_REGISTRATION_AGE = 18

CORS_ALLOWED_ORIGINS = env("CORS_ALLOWED_ORIGINS")

# Free ngrok requires this request header; browsers preflight it as a non-simple header.
CORS_ALLOW_HEADERS = list(default_headers) + [
    "ngrok-skip-browser-warning",
]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}
