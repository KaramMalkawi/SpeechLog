import os

from django.core.asgi import get_asgi_application

from config.settings import _SETTINGS_MODULE

os.environ.setdefault("DJANGO_SETTINGS_MODULE", _SETTINGS_MODULE)

application = get_asgi_application()
