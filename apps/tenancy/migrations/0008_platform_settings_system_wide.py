# Move gathering rules to system-wide PlatformSettings; drop per country/city overrides.

from django.db import migrations, models


def seed_platform_settings(apps, schema_editor):
    PlatformSettings = apps.get_model("tenancy", "PlatformSettings")
    PlatformSettings.objects.get_or_create(
        pk=1,
        defaults={
            "gathering_hard_cap": 20,
            "gathering_member_min_events": 1,
            "gathering_non_member_min_events": 3,
        },
    )


class Migration(migrations.Migration):
    dependencies = [
        ("tenancy", "0007_country_city_product_settings"),
    ]

    operations = [
        migrations.CreateModel(
            name="PlatformSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "gathering_hard_cap",
                    models.PositiveIntegerField(
                        default=20,
                        help_text="Max attendees allowed on any gathering (system-wide).",
                    ),
                ),
                (
                    "gathering_member_min_events",
                    models.PositiveIntegerField(
                        default=1,
                        help_text="Scanned events a Member/Founder needs before creating/joining gatherings.",
                    ),
                ),
                (
                    "gathering_non_member_min_events",
                    models.PositiveIntegerField(
                        default=3,
                        help_text="Scanned events a Non-Member needs before creating/joining gatherings.",
                    ),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "platform settings",
                "verbose_name_plural": "platform settings",
            },
        ),
        migrations.RunPython(seed_platform_settings, migrations.RunPython.noop),
        migrations.RemoveField(model_name="city", name="gathering_hard_cap"),
        migrations.RemoveField(model_name="city", name="gathering_member_min_events"),
        migrations.RemoveField(model_name="city", name="gathering_non_member_min_events"),
        migrations.RemoveField(model_name="country", name="gathering_hard_cap"),
        migrations.RemoveField(model_name="country", name="gathering_member_min_events"),
        migrations.RemoveField(model_name="country", name="gathering_non_member_min_events"),
    ]
