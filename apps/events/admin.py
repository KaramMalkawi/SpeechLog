from django.contrib import admin

from apps.events.models import Event, EventJoinRequest, EventNotification, EventTicket


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "community_id", "city_id", "starts_at", "is_cancelled", "capacity")
    list_filter = ("category", "is_cancelled")
    search_fields = ("title", "location")


@admin.register(EventJoinRequest)
class EventJoinRequestAdmin(admin.ModelAdmin):
    list_display = ("event", "user", "status", "requested_at", "responded_at")
    list_filter = ("status",)


@admin.register(EventTicket)
class EventTicketAdmin(admin.ModelAdmin):
    list_display = ("event", "user", "issued_at", "scanned_at", "is_active")
    list_filter = ("is_active",)
    search_fields = ("user__email", "event__title", "token")
    readonly_fields = ("token", "issued_at")
    actions = ("mark_scanned",)

    @admin.action(description="Mark selected tickets as scanned (attended)")
    def mark_scanned(self, request, queryset):
        from django.utils import timezone

        updated = queryset.filter(scanned_at__isnull=True, is_active=True).update(
            scanned_at=timezone.now()
        )
        self.message_user(request, f"Marked {updated} ticket(s) as scanned.")


@admin.register(EventNotification)
class EventNotificationAdmin(admin.ModelAdmin):
    list_display = ("event", "user", "notification_type", "delivered_at", "read_at")
    list_filter = ("notification_type",)
