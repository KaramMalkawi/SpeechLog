from django.db import migrations, models


def fix_locals_marked_verified_without_admin(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    User.objects.filter(
        resident_type="local",
        manual_verification_approved=False,
    ).update(
        verification_status="pending_review",
        registration_step=3,
    )


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0013_user_resident_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="manual_verification_approved",
            field=models.BooleanField(
                default=False,
                help_text="For Local residents: True only after an admin completes step 3 review.",
            ),
        ),
        migrations.RunPython(fix_locals_marked_verified_without_admin, migrations.RunPython.noop),
    ]
