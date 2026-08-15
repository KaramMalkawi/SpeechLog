from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0021_user_email_verified"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="location",
            field=models.CharField(
                blank=True,
                help_text="Free-text base location shown on the profile (e.g. city).",
                max_length=160,
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="profile_onboarding_completed",
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text=(
                    "True after the post-OTP profile setup screens are finished or "
                    "skipped. Identity (Didit) verification is separate and optional."
                ),
            ),
        ),
        # Existing email-verified accounts should not be forced through the new
        # post-OTP profile screens — only new registrations after this migration.
        migrations.RunSQL(
            sql=(
                "UPDATE accounts_user SET profile_onboarding_completed = TRUE "
                "WHERE email_verified = TRUE;"
            ),
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
