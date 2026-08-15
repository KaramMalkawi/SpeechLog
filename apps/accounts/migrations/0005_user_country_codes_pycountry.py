from django.db import migrations, models


def migrate_user_country_fields(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    for user in User.objects.select_related("nationality", "residence_country").iterator():
        updates = {}
        if user.nationality_id and user.nationality:
            updates["nationality_code"] = user.nationality.code
        if user.residence_country_id and user.residence_country:
            updates["residence_country_code"] = user.residence_country.code
        if updates:
            User.objects.filter(pk=user.pk).update(**updates)


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_user_residence_country"),
        ("tenancy", "0004_remove_allows_residence_cleanup"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="nationality_code",
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text="ISO 3166-1 alpha-2 nationality code (pycountry).",
                max_length=2,
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="residence_country_code",
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text="ISO 3166-1 alpha-2 country of residence.",
                max_length=2,
            ),
        ),
        migrations.RunPython(migrate_user_country_fields, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="user",
            name="nationality",
        ),
        migrations.RemoveField(
            model_name="user",
            name="residence_country",
        ),
    ]
