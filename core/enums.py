from django.db import models


class PartnerScope(models.TextChoices):
    """Guidebook partner visibility — used by partners app in a later milestone."""

    COMMUNITY = "community", "Community"
    CITY_WIDE = "city_wide", "City-wide"
