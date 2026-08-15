from .base import *  # noqa: F403

DEBUG = True

ALLOWED_HOSTS = env.list(  # noqa: F405
    "ALLOWED_HOSTS",
    default=["localhost", "127.0.0.1", "0.0.0.0", "*"],
)
# ngrok tunnels (subdomain changes each run on free tier)
ALLOWED_HOSTS += [".ngrok-free.dev", ".ngrok.io", ".ngrok.app"]
# Expo / physical devices call the API via the machine LAN IP (changes per network)
if "*" not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append("*")

SECRET_KEY = env("SECRET_KEY") or "local-dev-secret-key-not-for-production"  # noqa: F405

CORS_ALLOWED_ORIGINS = env.list(  # noqa: F405
    "CORS_ALLOWED_ORIGINS",
    default=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
)

CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])  # noqa: F405
CSRF_TRUSTED_ORIGINS += [
    "https://*.ngrok-free.dev",
    "https://*.ngrok.io",
    "https://*.ngrok.app",
]

# ngrok terminates TLS and forwards to the container over HTTP
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

API_DOCS_ENABLED = True

VERIFY_TEST_PAGE_ENABLED = True
DIDIT_CALLBACK_URL = env("DIDIT_CALLBACK_URL", default="http://localhost:8000/api/v1/accounts/verify-test/")  # noqa: F405
