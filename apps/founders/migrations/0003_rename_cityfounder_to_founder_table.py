import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("founders", "0002_copy_city_founders_from_accounts"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RenameModel(
            old_name="CityFounder",
            new_name="Founder",
        ),
        migrations.AlterModelTable(
            name="founder",
            table="city_founders",
        ),
        migrations.AlterField(
            model_name="founder",
            name="user",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="founder_profile",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RemoveIndex(
            model_name="founder",
            name="founders_ci_city_id_7caf31_idx",
        ),
        migrations.RemoveIndex(
            model_name="founder",
            name="founders_ci_status_6ee1c6_idx",
        ),
        migrations.AddIndex(
            model_name="founder",
            index=models.Index(
                fields=["city_id", "status"],
                name="city_founde_city_id_76fb2b_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="founder",
            index=models.Index(
                fields=["status", "created_at"],
                name="city_founde_status_6cd2f7_idx",
            ),
        ),
    ]
