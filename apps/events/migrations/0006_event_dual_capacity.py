# Dual expat/local event capacity pools

from django.db import migrations, models


def backfill_dual_capacity(apps, schema_editor):
    Event = apps.get_model("events", "Event")
    for event in Event.objects.all().iterator():
        total = event.capacity
        if total is None:
            # Former "unlimited" events get equal open pools.
            event.capacity_expatriates = 20
            event.capacity_locals = 20
        else:
            locals_n = total // 2
            event.capacity_expatriates = total - locals_n
            event.capacity_locals = locals_n
        event.save(update_fields=["capacity_expatriates", "capacity_locals"])


class Migration(migrations.Migration):
    dependencies = [
        ("events", "0005_gathering_attendance_and_ticket_scan"),
    ]

    operations = [
        migrations.AddField(
            model_name="event",
            name="capacity_expatriates",
            field=models.PositiveIntegerField(
                default=0,
                help_text="Max active tickets for users with resident_type=expatriate.",
            ),
        ),
        migrations.AddField(
            model_name="event",
            name="capacity_locals",
            field=models.PositiveIntegerField(
                default=0,
                help_text="Max active tickets for users with resident_type=local.",
            ),
        ),
        migrations.RunPython(backfill_dual_capacity, migrations.RunPython.noop),
    ]
