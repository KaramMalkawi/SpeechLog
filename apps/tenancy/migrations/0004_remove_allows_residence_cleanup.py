import uuid

from django.db import migrations


def cleanup_operational_countries(apps, schema_editor):
    Country = apps.get_model("tenancy", "Country")
    City = apps.get_model("tenancy", "City")

    jordan, _ = Country.objects.update_or_create(
        code="JO",
        defaults={
            "name": "Jordan",
            "slug": "jordan",
            "is_active": True,
        },
    )
    if not City.objects.filter(country=jordan, slug="amman").exists():
        City.objects.create(
            id=uuid.uuid4(),
            country=jordan,
            name="Amman",
            slug="amman",
            is_active=True,
        )

    referenced_country_ids = City.objects.values_list("country_id", flat=True).distinct()
    Country.objects.exclude(id__in=referenced_country_ids).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("tenancy", "0003_country_allows_residence_seed"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="country",
            name="allows_residence",
        ),
        migrations.RunPython(cleanup_operational_countries, migrations.RunPython.noop),
    ]
