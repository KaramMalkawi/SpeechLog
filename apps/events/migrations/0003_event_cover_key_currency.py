# Generated manually for cover key + currency

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("events", "0002_event_cover_invitation_token"),
    ]

    operations = [
        migrations.RenameField(
            model_name="event",
            old_name="cover_image_url",
            new_name="cover_image_key",
        ),
        migrations.AlterField(
            model_name="event",
            name="cover_image_key",
            field=models.CharField(
                blank=True,
                help_text="S3 object key for the event cover image.",
                max_length=512,
            ),
        ),
        migrations.AddField(
            model_name="event",
            name="currency",
            field=models.CharField(
                default="JOD",
                help_text="ISO 4217 currency code for price display.",
                max_length=3,
            ),
        ),
    ]
