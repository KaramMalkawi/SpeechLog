"""Select settings module from DJANGO_ENV in .env."""

import os

_ENV = os.environ.get("DJANGO_ENV", "local")
_SETTINGS_MODULE = f"config.settings.{_ENV}"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", _SETTINGS_MODULE)
