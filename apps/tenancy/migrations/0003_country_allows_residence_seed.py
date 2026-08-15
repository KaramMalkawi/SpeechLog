from django.db import migrations, models


def load_countries(apps, schema_editor):
    # Nationality catalog is served from pycountry; operational countries are seeded in 0004.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("tenancy", "0002_country_community_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="country",
            name="allows_residence",
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text="When True, users may select this country as their country of residence.",
            ),
        ),
        migrations.RunPython(load_countries, migrations.RunPython.noop),
    ]
