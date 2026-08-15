from .base import *  # noqa: F403

DEBUG = False

if not SECRET_KEY or SECRET_KEY == "insecure-dev-only-change-me":  # noqa: F405
    raise ValueError("SECRET_KEY must be set in production")

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31_536_000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
