import django.db.models.deletion
from django.db import migrations, models


def verify_staff_users(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    User.objects.filter(is_staff=True).update(
        verification_status="verified",
        registration_step=2,
    )


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
        ("tenancy", "0002_country_community_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="area",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="user",
            name="full_name",
            field=models.CharField(blank=True, max_length=160),
        ),
        migrations.AddField(
            model_name="user",
            name="passport_number",
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name="user",
            name="phone_number",
            field=models.CharField(blank=True, max_length=32),
        ),
        migrations.AddField(
            model_name="user",
            name="registration_step",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="user",
            name="verification_status",
            field=models.CharField(
                choices=[
                    ("unverified", "Unverified"),
                    ("pending_review", "Pending review"),
                    ("verified", "Verified"),
                    ("rejected", "Rejected"),
                ],
                db_index=True,
                default="unverified",
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="nationality",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="nationals",
                to="tenancy.country",
            ),
        ),
        migrations.AddIndex(
            model_name="user",
            index=models.Index(
                fields=["verification_status", "is_active"],
                name="accounts_us_verific_0f0a2a_idx",
            ),
        ),
        migrations.RunPython(verify_staff_users, migrations.RunPython.noop),
    ]
