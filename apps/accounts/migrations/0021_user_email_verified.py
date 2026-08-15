from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0020_user_must_change_password"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="email_verified",
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text="True after the user confirms ownership of their email via OTP.",
            ),
        ),
    ]
