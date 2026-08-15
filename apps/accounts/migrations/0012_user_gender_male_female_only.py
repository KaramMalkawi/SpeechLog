from django.db import migrations, models


def clear_non_binary_gender_values(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    User.objects.exclude(gender__in=["M", "F", ""]).update(gender="")


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0011_platform_role_admin"),
    ]

    operations = [
        migrations.RunPython(clear_non_binary_gender_values, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="user",
            name="gender",
            field=models.CharField(
                blank=True,
                choices=[("M", "Male"), ("F", "Female")],
                max_length=8,
            ),
        ),
    ]
