# Generated manually for Milestone 1 tenancy foundation

import uuid

import django.db.models.deletion
from django.db import migrations, models


def seed_countries_and_link_cities(apps, schema_editor):
    City = apps.get_model("tenancy", "City")
    Country = apps.get_model("tenancy", "Country")

    country_by_code: dict[str, object] = {}
    for city in City.objects.all():
        code = city.country_code.upper()
        if code not in country_by_code:
            country_by_code[code] = Country.objects.create(
                id=uuid.uuid4(),
                name=code,
                code=code,
                slug=code.lower(),
                is_active=True,
            )
        city.country = country_by_code[code]
        city.save(update_fields=["country"])


class Migration(migrations.Migration):

    dependencies = [
        ("tenancy", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Country",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=120)),
                ("code", models.CharField(db_index=True, max_length=2, unique=True)),
                ("slug", models.SlugField(max_length=120, unique=True)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={
                "verbose_name_plural": "countries",
                "ordering": ["name"],
            },
        ),
        migrations.AddField(
            model_name="city",
            name="country",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="cities",
                to="tenancy.country",
            ),
        ),
        migrations.RunPython(seed_countries_and_link_cities, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="city",
            name="country_code",
        ),
        migrations.AlterField(
            model_name="city",
            name="country",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="cities",
                to="tenancy.country",
            ),
        ),
        migrations.AlterField(
            model_name="city",
            name="slug",
            field=models.SlugField(max_length=120),
        ),
        migrations.AddConstraint(
            model_name="city",
            constraint=models.UniqueConstraint(
                fields=("country", "slug"),
                name="uniq_city_slug_per_country",
            ),
        ),
        migrations.AddIndex(
            model_name="city",
            index=models.Index(fields=["country", "is_active"], name="tenancy_cit_country_6e0f0a_idx"),
        ),
        migrations.AddField(
            model_name="community",
            name="community_type",
            field=models.CharField(
                choices=[
                    ("general", "General"),
                    ("nationality", "Nationality-specific"),
                    ("interest", "Interest-based"),
                ],
                db_index=True,
                default="general",
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="community",
            name="secondary_color",
            field=models.CharField(blank=True, max_length=7),
        ),
        migrations.AddField(
            model_name="community",
            name="tagline",
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddIndex(
            model_name="community",
            index=models.Index(
                fields=["city", "community_type"],
                name="tenancy_com_city_id_8b2c4d_idx",
            ),
        ),
    ]
