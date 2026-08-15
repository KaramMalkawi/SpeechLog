# Raise gathering DB ceiling so country/city product caps can exceed the old fixed 20.

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("gatherings", "0004_gathering_deletion_request_and_creator_not_attendee"),
        ("tenancy", "0007_country_city_product_settings"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="gathering",
            name="gathering_max_attendees_within_hard_cap",
        ),
        migrations.AlterField(
            model_name="gathering",
            name="max_attendees",
            field=models.PositiveIntegerField(
                default=20,
                validators=[
                    MinValueValidator(2),
                    MaxValueValidator(100),
                ],
            ),
        ),
        migrations.AddConstraint(
            model_name="gathering",
            constraint=models.CheckConstraint(
                condition=models.Q(max_attendees__gte=2)
                & models.Q(max_attendees__lte=100),
                name="gathering_max_attendees_within_hard_cap",
            ),
        ),
    ]
