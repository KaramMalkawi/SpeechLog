from django.db import migrations, models


def copy_extracted_names_to_official(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    Session = apps.get_model("accounts", "IdentityVerificationSession")
    seen_users: set = set()
    for session in Session.objects.exclude(extracted_full_name="").order_by("-created_at"):
        if session.user_id in seen_users:
            continue
        seen_users.add(session.user_id)
        User.objects.filter(pk=session.user_id).update(official_full_name=session.extracted_full_name)


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0007_rename_accounts_id_user_id_6d2f0a_idx_accounts_id_user_id_e5a2cb_idx_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="official_full_name",
            field=models.CharField(
                blank=True,
                help_text="Full name as read from the identity document (Didit OCR).",
                max_length=160,
            ),
        ),
        migrations.RunPython(copy_extracted_names_to_official, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="user",
            name="first_name",
        ),
        migrations.RemoveField(
            model_name="user",
            name="last_name",
        ),
        migrations.RemoveField(
            model_name="user",
            name="passport_number",
        ),
        migrations.RemoveField(
            model_name="identityverificationsession",
            name="extracted_document_number",
        ),
    ]
