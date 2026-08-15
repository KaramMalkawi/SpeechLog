# Generated manually for platform admin audit actions

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("adminpanel", "0006_profile_update_audit_action"),
    ]

    operations = [
        migrations.AlterField(
            model_name="adminauditlog",
            name="action",
            field=models.CharField(
                choices=[
                    ("admin.login", "Admin login"),
                    ("city_founder.create", "Create city founder"),
                    ("city_founder.update", "Update city founder"),
                    ("city_founder.delete", "Delete city founder"),
                    ("admin.create", "Create admin"),
                    ("admin.update", "Update admin"),
                    ("admin.delete", "Delete admin"),
                    ("user.delete", "Delete user"),
                    ("user.role_update", "Update user role"),
                    ("admin.password_change", "Change password"),
                    ("admin.profile_update", "Update profile"),
                ],
                db_index=True,
                max_length=64,
            ),
        ),
    ]
