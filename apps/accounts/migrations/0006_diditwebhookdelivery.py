from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0005_user_country_codes_pycountry"),
    ]

    operations = [
        migrations.CreateModel(
            name="DiditWebhookDelivery",
            fields=[
                ("event_id", models.UUIDField(primary_key=True, serialize=False)),
                ("webhook_type", models.CharField(blank=True, max_length=64)),
                ("received_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["-received_at"],
            },
        ),
    ]
