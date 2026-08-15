# Generated manually for platform settings audit action

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("adminpanel", "0010_geography_audit_actions"),
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
                    ("gathering.deletion_approve", "Approve gathering deletion"),
                    ("gathering.deletion_reject", "Reject gathering deletion"),
                    ("country.create", "Create country"),
                    ("country.update", "Update country"),
                    ("city.create", "Create city"),
                    ("city.update", "Update city"),
                    ("platform_settings.update", "Update platform settings"),
                ],
                db_index=True,
                max_length=64,
            ),
        ),
    ]
