from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("tasks", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="SandboxSession",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("container_id", models.CharField(max_length=128, unique=True)),
                ("repo_path", models.CharField(max_length=255)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("starting", "Starting"),
                            ("active", "Active"),
                            ("stopped", "Stopped"),
                            ("expired", "Expired"),
                            ("failed", "Failed"),
                        ],
                        default="starting",
                        max_length=10,
                    ),
                ),
                ("timeout_seconds", models.PositiveSmallIntegerField(default=30)),
                ("max_repo_size_mb", models.PositiveSmallIntegerField(default=10)),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("last_activity_at", models.DateTimeField(auto_now=True)),
                ("expires_at", models.DateTimeField()),
                (
                    "task",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="sandbox_sessions",
                        to="tasks.task",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="sandbox_sessions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-last_activity_at"]},
        ),
        migrations.AddConstraint(
            model_name="sandboxsession",
            constraint=models.CheckConstraint(
                condition=models.Q(("timeout_seconds__gte", 1), ("timeout_seconds__lte", 300)),
                name="sandbox_timeout_seconds_range",
            ),
        ),
        migrations.AddConstraint(
            model_name="sandboxsession",
            constraint=models.CheckConstraint(
                condition=models.Q(("max_repo_size_mb__gte", 1), ("max_repo_size_mb__lte", 1024)),
                name="sandbox_repo_size_mb_range",
            ),
        ),
        migrations.AddIndex(
            model_name="sandboxsession",
            index=models.Index(fields=["user", "status"], name="sandbox_sa_user_id_a73fbe_idx"),
        ),
        migrations.AddIndex(
            model_name="sandboxsession",
            index=models.Index(fields=["expires_at"], name="sandbox_sa_expires_905f43_idx"),
        ),
    ]
