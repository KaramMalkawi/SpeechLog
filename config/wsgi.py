import os

from django.core.wsgi import get_wsgi_application

from config.settings import _SETTINGS_MODULE

os.environ.setdefault("DJANGO_SETTINGS_MODULE", _SETTINGS_MODULE)

application = get_wsgi_application()
