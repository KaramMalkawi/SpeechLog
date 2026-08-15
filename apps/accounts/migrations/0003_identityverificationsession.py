import uuid

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_user_registration_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="IdentityVerificationSession",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("provider", models.CharField(choices=[("didit", "Didit")], default="didit", max_length=32)),
                ("provider_session_id", models.UUIDField(db_index=True)),
                ("status", models.CharField(default="Not Started", max_length=64)),
                ("verification_url", models.URLField(blank=True, max_length=500)),
                ("extracted_full_name", models.CharField(blank=True, max_length=160)),
                ("extracted_nationality", models.CharField(blank=True, max_length=3)),
                ("extracted_document_number", models.CharField(blank=True, max_length=64)),
                ("last_event_id", models.UUIDField(blank=True, db_index=True, null=True)),
                ("decision_payload", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="verification_sessions",
                        to="accounts.user",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["user", "status"], name="accounts_id_user_id_6d2f0a_idx"),
                ],
            },
        ),
    ]
