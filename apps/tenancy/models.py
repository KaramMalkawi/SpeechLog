from __future__ import annotations

from django.db import models

from core.models import CityScopedModel, TenantScopedModel, UUIDPrimaryKeyModel


class Country(UUIDPrimaryKeyModel):
    """Operational country for city/tenancy structure — not the nationality catalog."""

    name = models.CharField(max_length=120)
    code = models.CharField(max_length=2, unique=True, db_index=True)
    slug = models.SlugField(max_length=120, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "countries"

    def __str__(self) -> str:
        return self.name


class City(UUIDPrimaryKeyModel):
    country = models.ForeignKey(Country, on_delete=models.PROTECT, related_name="cities")
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=120)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["country", "slug"], name="uniq_city_slug_per_country"),
        ]
        indexes = [
            models.Index(fields=["country", "is_active"]),
        ]

    def __str__(self) -> str:
        return self.name


class Community(UUIDPrimaryKeyModel):
    class CommunityType(models.TextChoices):
        GENERAL = "general", "General"
        NATIONALITY = "nationality", "Nationality-specific"
        INTEREST = "interest", "Interest-based"

    city = models.ForeignKey(City, on_delete=models.PROTECT, related_name="communities")
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=160)
    community_type = models.CharField(
        max_length=32,
        choices=CommunityType.choices,
        default=CommunityType.GENERAL,
        db_index=True,
    )
    primary_color = models.CharField(max_length=7, default="#000000")
    secondary_color = models.CharField(max_length=7, blank=True)
    logo_url = models.URLField(blank=True)
    tagline = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["city", "slug"], name="uniq_community_slug_per_city"),
        ]
        indexes = [
            models.Index(fields=["city", "is_active"]),
            models.Index(fields=["city", "community_type"]),
        ]

    def __str__(self) -> str:
        return self.name


class CityAnnouncement(CityScopedModel):
    """City-shared content visible across communities in the same city."""

    title = models.CharField(max_length=200)
    body = models.TextField()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title


class CommunityAnnouncement(TenantScopedModel):
    """Community-isolated content for tenancy isolation tests and future features."""

    title = models.CharField(max_length=200)
    body = models.TextField()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title
