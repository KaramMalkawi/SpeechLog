from django.db import migrations, models


def promote_superusers_to_admin(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    User.objects.filter(is_superuser=True, is_staff=True).update(platform_role="admin")


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0010_user_platform_role"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="platform_role",
            field=models.CharField(
                choices=[
                    ("non_member", "Non-Member"),
                    ("member", "Member"),
                    ("admin", "Admin"),
                ],
                db_index=True,
                default="non_member",
                help_text="Platform access tier. Registration defaults to Non-Member; superusers are Admin.",
                max_length=32,
            ),
        ),
        migrations.RunPython(promote_superusers_to_admin, migrations.RunPython.noop),
    ]
