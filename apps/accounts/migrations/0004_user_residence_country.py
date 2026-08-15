import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_identityverificationsession"),
        ("tenancy", "0003_country_allows_residence_seed"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="user",
            name="area",
        ),
        migrations.AddField(
            model_name="user",
            name="residence_country",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="residents",
                to="tenancy.country",
            ),
        ),
    ]
