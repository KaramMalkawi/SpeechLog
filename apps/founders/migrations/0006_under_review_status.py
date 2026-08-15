from django.db import migrations, models


def forwards(apps, schema_editor):
    FounderApplication = apps.get_model("founders", "FounderApplication")
    FounderApplication.objects.filter(status="not_reviewed").update(status="under_review")


def backwards(apps, schema_editor):
    FounderApplication = apps.get_model("founders", "FounderApplication")
    FounderApplication.objects.filter(status="under_review").update(status="not_reviewed")


class Migration(migrations.Migration):

    dependencies = [
        ("founders", "0005_founder_applications"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
        migrations.AlterField(
            model_name="founderapplication",
            name="status",
            field=models.CharField(
                choices=[
                    ("under_review", "Under review"),
                    ("reviewed", "Reviewed"),
                    ("accepted", "Accepted"),
                    ("rejected", "Rejected"),
                ],
                db_index=True,
                default="under_review",
                max_length=32,
            ),
        ),
    ]
