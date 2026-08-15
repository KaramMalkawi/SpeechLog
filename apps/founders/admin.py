from django.contrib import admin

from apps.founders.models import Founder, FounderApplication, FounderApplicationSyncState


@admin.register(Founder)
class FounderAdmin(admin.ModelAdmin):
    list_display = ("user", "city_id", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("user__email", "user__full_name")
    raw_id_fields = ("user",)


@admin.register(FounderApplication)
class FounderApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "email",
        "country_name",
        "status",
        "submitted_at",
        "sheet_row",
        "updated_at",
    )
    list_filter = ("status",)
    search_fields = ("email", "country_name", "full_name")
    readonly_fields = (
        "sheet_row",
        "submitted_at",
        "email",
        "country_name",
        "full_name",
        "answers",
        "spreadsheet_id",
        "sheet_gid",
        "created_at",
        "updated_at",
    )


@admin.register(FounderApplicationSyncState)
class FounderApplicationSyncStateAdmin(admin.ModelAdmin):
    list_display = (
        "last_synced_at",
        "last_sync_row_count",
        "spreadsheet_id",
        "updated_at",
    )
    readonly_fields = (
        "last_synced_at",
        "last_sync_error",
        "last_sync_row_count",
        "spreadsheet_id",
        "spreadsheet_url",
        "updated_at",
    )
