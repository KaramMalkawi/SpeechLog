from __future__ import annotations

from rest_framework import serializers

from apps.accounts.models import User
from apps.guidebook.models import Partner
from apps.guidebook.selectors import (
    category_label,
    discount_label,
    get_image_url,
    resolve_city_name,
    viewer_partner_access,
)


class PartnerSerializer(serializers.ModelSerializer):
    city_name = serializers.SerializerMethodField()
    category_label = serializers.SerializerMethodField()
    discount_label = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
    cover_image_url = serializers.SerializerMethodField()
    map_image_url = serializers.SerializerMethodField()
    viewer_access = serializers.SerializerMethodField()

    class Meta:
        model = Partner
        fields = [
            "id",
            "scope",
            "community_id",
            "city_id",
            "city_name",
            "name",
            "category",
            "category_label",
            "area",
            "short_description",
            "description",
            "discount_percent",
            "discount_label",
            "rating",
            "address",
            "hours_label",
            "hours_range",
            "website",
            "website_url",
            "maps_url",
            "image_url",
            "cover_image_url",
            "map_image_url",
            "is_active",
            "sort_order",
            "viewer_access",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def _viewer(self) -> User | None:
        request = self.context.get("request")
        if request is None:
            return None
        user = getattr(request, "user", None)
        if user is not None and getattr(user, "is_authenticated", False):
            return user
        return None

    def get_city_name(self, partner: Partner) -> str:
        return resolve_city_name(city_id=partner.city_id)

    def get_category_label(self, partner: Partner) -> str:
        return category_label(partner.category)

    def get_discount_label(self, partner: Partner) -> str:
        return discount_label(percent=partner.discount_percent)

    def get_image_url(self, partner: Partner) -> str:
        return get_image_url(partner.image_key)

    def get_cover_image_url(self, partner: Partner) -> str:
        return get_image_url(partner.cover_image_key or partner.image_key)

    def get_map_image_url(self, partner: Partner) -> str:
        return get_image_url(partner.map_image_key)

    def get_viewer_access(self, partner: Partner) -> str:
        return viewer_partner_access(viewer=self._viewer())
