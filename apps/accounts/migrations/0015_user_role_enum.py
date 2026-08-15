from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0014_user_manual_verification_approved"),
    ]

    operations = [
        migrations.RenameField(
            model_name="user",
            old_name="platform_role",
            new_name="role",
        ),
        migrations.AlterField(
            model_name="user",
            name="role",
            field=models.CharField(
                choices=[
                    ("admin", "Admin"),
                    ("city_founder", "City Founder"),
                    ("team_member", "Team Member"),
                    ("member", "Member"),
                    ("non_member", "Non-Member"),
                ],
                db_index=True,
                default="non_member",
                help_text="Platform role. Registration defaults to Non-Member.",
                max_length=32,
            ),
        ),
    ]
