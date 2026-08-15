from django.db import migrations


def copy_city_founders_forward(apps, schema_editor):
    connection = schema_editor.connection
    with connection.cursor() as cursor:
        tables = set(connection.introspection.table_names(cursor))
        if "accounts_cityfounder" not in tables:
            return
        if "founders_cityfounder" not in tables:
            return
        cursor.execute(
            """
            INSERT INTO founders_cityfounder (
                id, created_at, updated_at, city_id, status, user_id
            )
            SELECT
                id, created_at, updated_at, city_id, status, user_id
            FROM accounts_cityfounder
            ON CONFLICT (id) DO NOTHING
            """
        )


def copy_city_founders_backward(apps, schema_editor):
    connection = schema_editor.connection
    with connection.cursor() as cursor:
        tables = set(connection.introspection.table_names(cursor))
        if "accounts_cityfounder" not in tables:
            return
        if "founders_cityfounder" not in tables:
            return
        cursor.execute(
            """
            INSERT INTO accounts_cityfounder (
                id, created_at, updated_at, city_id, status, user_id
            )
            SELECT
                id, created_at, updated_at, city_id, status, user_id
            FROM founders_cityfounder
            ON CONFLICT (id) DO NOTHING
            """
        )


class Migration(migrations.Migration):

    dependencies = [
        ("founders", "0001_move_city_founder_to_founders_app"),
    ]

    operations = [
        migrations.RunPython(
            copy_city_founders_forward,
            copy_city_founders_backward,
        ),
    ]
