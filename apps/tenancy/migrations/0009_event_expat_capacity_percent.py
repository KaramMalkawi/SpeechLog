# Add system-wide expat seat share for events

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tenancy", "0008_platform_settings_system_wide"),
    ]

    operations = [
        migrations.AddField(
            model_name="platformsettings",
            name="event_expat_capacity_percent",
            field=models.PositiveSmallIntegerField(
                default=50,
                help_text=(
                    "Share of each event’s total capacity reserved for expatriates (0–100). "
                    "Locals get the remainder. Applied live to all events."
                ),
            ),
        ),
    ]
