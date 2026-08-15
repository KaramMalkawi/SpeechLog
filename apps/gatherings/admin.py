from django.contrib import admin

from apps.gatherings.models import Gathering, GatheringAttendee


@admin.register(Gathering)
class GatheringAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "community_id",
        "city_id",
        "starts_at",
        "max_attendees",
        "is_cancelled",
    )
    search_fields = ("title", "area")
    list_filter = ("is_cancelled",)


@admin.register(GatheringAttendee)
class GatheringAttendeeAdmin(admin.ModelAdmin):
    list_display = ("gathering", "user", "joined_at", "is_active")
    list_filter = ("is_active",)
