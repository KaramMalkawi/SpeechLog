from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0015_user_role_enum"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="bio",
            field=models.CharField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name="user",
            name="profile_photo_key",
            field=models.CharField(
                blank=True,
                help_text="S3 object key for the user's profile photo.",
                max_length=512,
            ),
        ),
        migrations.CreateModel(
            name="UserFollow",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "follower",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="following_relations",
                        to="accounts.user",
                    ),
                ),
                (
                    "following",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="follower_relations",
                        to="accounts.user",
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(fields=["follower", "created_at"], name="accounts_us_followe_0f0f62_idx"),
                    models.Index(fields=["following", "created_at"], name="accounts_us_followi_4a3f1d_idx"),
                ],
                "constraints": [
                    models.UniqueConstraint(fields=("follower", "following"), name="uniq_user_follow"),
                    models.CheckConstraint(
                        condition=~models.Q(follower=models.F("following")),
                        name="prevent_self_follow",
                    ),
                ],
            },
        ),
    ]
