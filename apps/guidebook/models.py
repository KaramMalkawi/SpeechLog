from __future__ import annotations

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from core.models import CityScopedModel


class PartnerCategory(models.TextChoices):
    RESTAURANT = "restaurant", "Restaurant"
    GROCERY = "grocery", "Grocery"
    TRANSPORT = "transport", "Transport"
    FITNESS = "fitness", "Fitness"
    ENTERTAINMENT = "entertainment", "Entertainment"
    OTHER = "other", "Other"


class PartnerScope(models.TextChoices):
    CITY_WIDE = "city_wide", "City-wide"
    COMMUNITY = "community", "Community"


class Partner(CityScopedModel):
    """
    Guidebook partner discount listing.

    City-wide partners carry city_id only (visible to every community in that city).
    Community-scoped partners also set community_id (isolated to one community).
    """

    scope = models.CharField(
        max_length=32,
        choices=PartnerScope.choices,
        default=PartnerScope.CITY_WIDE,
        db_index=True,
    )
    community_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Required when scope=community; must be null for city_wide.",
    )
    name = models.CharField(max_length=200)
    category = models.CharField(
        max_length=64,
        choices=PartnerCategory.choices,
        default=PartnerCategory.RESTAURANT,
        db_index=True,
    )
    area = models.CharField(max_length=120, blank=True)
    short_description = models.CharField(max_length=280, blank=True)
    description = models.TextField(blank=True)
    discount_percent = models.PositiveSmallIntegerField(
        default=15,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
    )
    rating = models.DecimalField(
        max_digits=2,
        decimal_places=1,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
    )
    address = models.CharField(max_length=255, blank=True)
    hours_label = models.CharField(max_length=64, blank=True)
    hours_range = models.CharField(max_length=64, blank=True)
    website = models.CharField(max_length=200, blank=True)
    website_url = models.URLField(max_length=500, blank=True)
    maps_url = models.URLField(max_length=500, blank=True)
    image_key = models.CharField(
        max_length=512,
        blank=True,
        help_text="S3 object key for the list-card image.",
    )
    cover_image_key = models.CharField(
        max_length=512,
        blank=True,
        help_text="S3 object key for the detail hero image.",
    )
    map_image_key = models.CharField(
        max_length=512,
        blank=True,
        help_text="S3 object key for the location map preview.",
    )
    is_active = models.BooleanField(default=True, db_index=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]
        indexes = [
            models.Index(fields=["city_id", "is_active", "sort_order"]),
            models.Index(fields=["city_id", "category"]),
            models.Index(fields=["community_id", "is_active"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(scope="city_wide", community_id__isnull=True)
                    | models.Q(scope="community", community_id__isnull=False)
                ),
                name="partner_scope_matches_community_id",
            ),
        ]

    def __str__(self) -> str:
        return self.name
