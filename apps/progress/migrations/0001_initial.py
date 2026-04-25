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
            name="HintUsage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("hint_index", models.PositiveSmallIntegerField()),
                ("points_spent", models.PositiveSmallIntegerField(default=0)),
                ("unlocked_at", models.DateTimeField(auto_now_add=True)),
                (
                    "task",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="hint_usages",
                        to="tasks.task",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="hint_usages",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-unlocked_at"]},
        ),
        migrations.CreateModel(
            name="LeaderboardSnapshot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("total_points", models.PositiveIntegerField(default=0)),
                ("rank", models.PositiveIntegerField(default=1)),
                ("captured_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="leaderboard_snapshots",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["captured_at", "rank"]},
        ),
        migrations.CreateModel(
            name="TaskAttempt",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("attempt_no", models.PositiveIntegerField(default=1)),
                (
                    "verdict",
                    models.CharField(
                        choices=[("failed", "Failed"), ("passed", "Passed"), ("error", "Error")],
                        default="failed",
                        max_length=10,
                    ),
                ),
                ("diagnostics", models.TextField(blank=True)),
                ("duration_ms", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "task",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attempts",
                        to="tasks.task",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="task_attempts",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="TaskCompletion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("points_awarded", models.PositiveSmallIntegerField(default=0)),
                ("completed_at", models.DateTimeField(auto_now_add=True)),
                (
                    "task",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="completions",
                        to="tasks.task",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="completed_tasks",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-completed_at"]},
        ),
        migrations.AddConstraint(
            model_name="taskattempt",
            constraint=models.UniqueConstraint(
                fields=("user", "task", "attempt_no"),
                name="progress_unique_attempt_number",
            ),
        ),
        migrations.AddConstraint(
            model_name="taskcompletion",
            constraint=models.UniqueConstraint(fields=("user", "task"), name="progress_unique_completion"),
        ),
        migrations.AddConstraint(
            model_name="taskcompletion",
            constraint=models.CheckConstraint(
                condition=models.Q(("points_awarded__gte", 0)),
                name="progress_points_awarded_non_negative",
            ),
        ),
        migrations.AddConstraint(
            model_name="hintusage",
            constraint=models.UniqueConstraint(
                fields=("user", "task", "hint_index"),
                name="progress_unique_hint_usage",
            ),
        ),
        migrations.AddConstraint(
            model_name="hintusage",
            constraint=models.CheckConstraint(
                condition=models.Q(("hint_index__gte", 1)),
                name="progress_hint_index_positive",
            ),
        ),
        migrations.AddConstraint(
            model_name="leaderboardsnapshot",
            constraint=models.CheckConstraint(condition=models.Q(("rank__gte", 1)), name="progress_rank_positive"),
        ),
        migrations.AddIndex(
            model_name="taskattempt",
            index=models.Index(fields=["user", "task", "-created_at"], name="progress_ta_user_id_53bfd2_idx"),
        ),
        migrations.AddIndex(
            model_name="taskcompletion",
            index=models.Index(fields=["user", "-completed_at"], name="progress_tc_user_id_eb74de_idx"),
        ),
        migrations.AddIndex(
            model_name="hintusage",
            index=models.Index(fields=["user", "task"], name="progress_hu_user_id_1dc456_idx"),
        ),
        migrations.AddIndex(
            model_name="leaderboardsnapshot",
            index=models.Index(fields=["captured_at", "rank"], name="progress_lb_captured_2be9a6_idx"),
        ),
    ]
