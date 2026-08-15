import os

from celery import Celery

from config.settings import _SETTINGS_MODULE

os.environ.setdefault("DJANGO_SETTINGS_MODULE", _SETTINGS_MODULE)

app = Celery("mixed_miles")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
