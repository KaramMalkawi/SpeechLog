from .base import *  # noqa: F403

DEBUG = True
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["*"])  # noqa: F405

if not SECRET_KEY or SECRET_KEY == "insecure-dev-only-change-me":  # noqa: F405
    raise ValueError("SECRET_KEY must be set in dev environment")

CORS_ALLOWED_ORIGINS = env.list(  # noqa: F405
    "CORS_ALLOWED_ORIGINS",
    default=[],
)

API_DOCS_ENABLED = True
