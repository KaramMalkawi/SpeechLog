from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0009_user_identity_document_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="platform_role",
            field=models.CharField(
                choices=[("non_member", "Non-Member"), ("member", "Member")],
                db_index=True,
                default="non_member",
                help_text="Platform access tier. New accounts are Non-Member until changed in admin.",
                max_length=32,
            ),
        ),
    ]
