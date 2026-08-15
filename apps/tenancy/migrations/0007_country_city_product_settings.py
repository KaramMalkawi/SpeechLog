# Generated manually for country/city product settings

from django.db import migrations, models


def seed_jordan_settings(apps, schema_editor):
    Country = apps.get_model("tenancy", "Country")
    Country.objects.filter(code="JO").update(
        currency="JOD",
        gathering_hard_cap=20,
        gathering_member_min_events=1,
        gathering_non_member_min_events=3,
        allows_residence=True,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("tenancy", "0006_country_currency"),
    ]

    operations = [
        migrations.AddField(
            model_name="country",
            name="gathering_hard_cap",
            field=models.PositiveIntegerField(
                default=20,
                help_text="Max attendees allowed on gatherings in this country (cities may override).",
            ),
        ),
        migrations.AddField(
            model_name="country",
            name="gathering_member_min_events",
            field=models.PositiveIntegerField(
                default=1,
                help_text="Scanned events a Member/Founder needs before creating/joining gatherings.",
            ),
        ),
        migrations.AddField(
            model_name="country",
            name="gathering_non_member_min_events",
            field=models.PositiveIntegerField(
                default=3,
                help_text="Scanned events a Non-Member needs before creating/joining gatherings.",
            ),
        ),
        migrations.AddField(
            model_name="country",
            name="allows_residence",
            field=models.BooleanField(
                default=False,
                help_text="Whether this country appears in the residence country picker.",
            ),
        ),
        migrations.AddField(
            model_name="city",
            name="gathering_hard_cap",
            field=models.PositiveIntegerField(
                blank=True,
                help_text="Override country gathering hard cap. Leave empty to inherit.",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="city",
            name="gathering_member_min_events",
            field=models.PositiveIntegerField(
                blank=True,
                help_text="Override country member gathering eligibility. Leave empty to inherit.",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="city",
            name="gathering_non_member_min_events",
            field=models.PositiveIntegerField(
                blank=True,
                help_text="Override country non-member gathering eligibility. Leave empty to inherit.",
                null=True,
            ),
        ),
        migrations.RunPython(seed_jordan_settings, migrations.RunPython.noop),
    ]
