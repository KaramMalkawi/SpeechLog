# Generated manually for Country.currency

from django.db import migrations, models


def seed_jordan_currency(apps, schema_editor):
    Country = apps.get_model("tenancy", "Country")
    Country.objects.filter(code="JO").update(currency="JOD")


class Migration(migrations.Migration):
    dependencies = [
        ("tenancy", "0005_rename_tenancy_cit_country_6e0f0a_idx_tenancy_cit_country_4d3f65_idx_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="country",
            name="currency",
            field=models.CharField(
                default="JOD",
                help_text="ISO 4217 currency code used for events and pricing in this country.",
                max_length=3,
            ),
        ),
        migrations.RunPython(seed_jordan_currency, migrations.RunPython.noop),
    ]
