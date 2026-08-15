from django.db import migrations


def clear_non_superuser_django_access(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    through_groups = User.groups.through
    through_perms = User.user_permissions.through

    non_superusers = User.objects.filter(is_superuser=False)
    non_superusers.filter(is_staff=True).update(is_staff=False)
    through_groups.objects.filter(user__is_superuser=False).delete()
    through_perms.objects.filter(user__is_superuser=False).delete()


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0018_move_city_founder_to_founders_app"),
    ]

    operations = [
        migrations.RunPython(clear_non_superuser_django_access, noop_reverse),
    ]
