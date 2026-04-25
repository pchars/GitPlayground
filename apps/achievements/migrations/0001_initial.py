from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Achievement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.SlugField(max_length=80, unique=True)),
                ("title", models.CharField(max_length=120)),
                ("description", models.TextField()),
                ("points_bonus", models.PositiveSmallIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["title"]},
        ),
        migrations.CreateModel(
            name="UserAchievement",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("awarded_at", models.DateTimeField(auto_now_add=True)),
                (
                    "achievement",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="users",
                        to="achievements.achievement",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="achievements",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-awarded_at"]},
        ),
        migrations.AddConstraint(
            model_name="userachievement",
            constraint=models.UniqueConstraint(
                fields=("user", "achievement"),
                name="achievements_unique_user_achievement",
            ),
        ),
        migrations.AddIndex(
            model_name="userachievement",
            index=models.Index(fields=["user", "awarded_at"], name="achievement_user_id_179db8_idx"),
        ),
    ]
