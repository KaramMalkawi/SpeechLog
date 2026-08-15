from django.contrib import admin

from apps.guidebook.models import Partner


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "category",
        "scope",
        "city_id",
        "community_id",
        "discount_percent",
        "is_active",
        "sort_order",
    )
    list_filter = ("scope", "category", "is_active")
    search_fields = ("name", "area", "address")
