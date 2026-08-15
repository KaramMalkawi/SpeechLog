from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0017_city_founder_and_audit_actions"),
        ("founders", "0002_copy_city_founders_from_accounts"),
    ]

    operations = [
        migrations.DeleteModel(
            name="CityFounder",
        ),
    ]
