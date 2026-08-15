from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0012_user_gender_male_female_only"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="resident_type",
            field=models.CharField(
                blank=True,
                choices=[("expatriate", "Expatriate"), ("local", "Local")],
                db_index=True,
                help_text="Expatriate when passport nationality matches residence country; Local when they differ.",
                max_length=32,
            ),
        ),
    ]
