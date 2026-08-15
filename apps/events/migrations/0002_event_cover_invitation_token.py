# Generated manually for cover image, invitation type, ticket token required, indexes

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("events", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="event",
            name="cover_image_url",
            field=models.URLField(blank=True, max_length=500),
        ),
        migrations.AddIndex(
            model_name="event",
            index=models.Index(
                fields=["community_id", "starts_at"],
                name="events_even_communi_7f2a1c_idx",
            ),
        ),
        migrations.AlterField(
            model_name="eventnotification",
            name="notification_type",
            field=models.CharField(
                choices=[
                    ("ticket", "Ticket"),
                    ("invitation", "Invitation"),
                    ("update", "Update"),
                    ("cancellation", "Cancellation"),
                ],
                db_index=True,
                default="ticket",
                max_length=32,
            ),
        ),
        migrations.AlterField(
            model_name="eventticket",
            name="token",
            field=models.CharField(max_length=512, unique=True),
        ),
    ]
