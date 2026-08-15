import os
import sys

from config.settings import _SETTINGS_MODULE  # noqa: F401


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", _SETTINGS_MODULE)
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
