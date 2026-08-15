from django.db import migrations


def backfill_display_names_from_official(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    for user in User.objects.exclude(official_full_name="").iterator():
        parts = [part for part in str(user.official_full_name or "").split() if part]
        if not parts:
            continue
        if len(parts) == 1:
            desired = parts[0][:160]
        else:
            desired = f"{parts[0]} {parts[-1]}"[:160]
        if user.full_name == desired:
            continue
        user.full_name = desired
        user.save(update_fields=["full_name"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0023_gathering_attendance_and_ticket_scan"),
    ]

    operations = [
        migrations.RunPython(backfill_display_names_from_official, noop_reverse),
    ]
