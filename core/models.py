from __future__ import annotations

import uuid

from django.db import models

from core.managers import CityScopedManager, TenantAwareManager


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UUIDPrimaryKeyModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class TenantScopedModel(UUIDPrimaryKeyModel, TimeStampedModel):
    """Community-isolated row; carries both community_id and denormalized city_id."""

    community_id = models.UUIDField(db_index=True)
    city_id = models.UUIDField(db_index=True)

    objects = TenantAwareManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True


class CityScopedModel(UUIDPrimaryKeyModel, TimeStampedModel):
    """City-shared row; visible across communities in the same city."""

    city_id = models.UUIDField(db_index=True)

    objects = CityScopedManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True
