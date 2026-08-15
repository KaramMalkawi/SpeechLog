from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0008_user_official_full_name_cleanup"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="age",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="user",
            name="date_of_birth",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="user",
            name="document_expiration_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="user",
            name="gender",
            field=models.CharField(
                blank=True,
                choices=[("M", "Male"), ("F", "Female"), ("X", "Other"), ("U", "Unknown")],
                max_length=8,
            ),
        ),
        migrations.AddField(
            model_name="identityverificationsession",
            name="extracted_date_of_birth",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="identityverificationsession",
            name="extracted_expiration_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="identityverificationsession",
            name="extracted_gender",
            field=models.CharField(blank=True, max_length=8),
        ),
    ]
