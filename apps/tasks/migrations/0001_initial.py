from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Level",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("number", models.PositiveSmallIntegerField(unique=True)),
                ("title", models.CharField(max_length=128)),
                ("slug", models.SlugField(max_length=64, unique=True)),
                ("description", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={"ordering": ["number"]},
        ),
        migrations.CreateModel(
            name="Task",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("external_id", models.CharField(max_length=64, unique=True)),
                ("slug", models.SlugField(max_length=80, unique=True)),
                ("title", models.CharField(max_length=150)),
                ("description", models.TextField()),
                ("order", models.PositiveSmallIntegerField()),
                ("points", models.PositiveSmallIntegerField()),
                ("validator_cmd", models.CharField(default="python validator.py", max_length=255)),
                ("success_message", models.CharField(blank=True, max_length=255)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "level",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="tasks",
                        to="tasks.level",
                    ),
                ),
            ],
            options={"ordering": ["level__number", "order", "id"]},
        ),
        migrations.CreateModel(
            name="TheoryBlock",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=128)),
                ("content_md", models.TextField()),
                ("diagram_mermaid", models.TextField(blank=True)),
                ("sandbox_preset", models.JSONField(blank=True, default=dict)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "level",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="theory",
                        to="tasks.level",
                    ),
                ),
            ],
            options={"ordering": ["level__number"]},
        ),
        migrations.CreateModel(
            name="TaskAsset",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "asset_type",
                    models.CharField(
                        choices=[
                            ("manifest", "Manifest"),
                            ("start_repo", "Start repository"),
                            ("validator", "Validator"),
                            ("hint", "Hint"),
                            ("theory", "Theory"),
                        ],
                        max_length=20,
                    ),
                ),
                ("path", models.CharField(max_length=255)),
                ("content", models.TextField(blank=True)),
                ("sort_order", models.PositiveSmallIntegerField(default=1)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "task",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="assets",
                        to="tasks.task",
                    ),
                ),
            ],
            options={"ordering": ["task__level__number", "task__order", "sort_order", "id"]},
        ),
        migrations.AddConstraint(
            model_name="level",
            constraint=models.CheckConstraint(
                condition=models.Q(("number__gte", 1), ("number__lte", 6)),
                name="tasks_level_number_1_6",
            ),
        ),
        migrations.AddConstraint(
            model_name="task",
            constraint=models.UniqueConstraint(fields=("level", "order"), name="tasks_unique_level_order"),
        ),
        migrations.AddConstraint(
            model_name="task",
            constraint=models.CheckConstraint(condition=models.Q(("points__gte", 1)), name="tasks_points_positive"),
        ),
        migrations.AddConstraint(
            model_name="task",
            constraint=models.CheckConstraint(condition=models.Q(("order__gte", 1)), name="tasks_order_positive"),
        ),
        migrations.AddConstraint(
            model_name="taskasset",
            constraint=models.CheckConstraint(
                condition=models.Q(("sort_order__gte", 1)),
                name="tasks_asset_order_positive",
            ),
        ),
        migrations.AddIndex(
            model_name="task",
            index=models.Index(fields=["level", "order"], name="tasks_task_level_i_0f9522_idx"),
        ),
        migrations.AddIndex(
            model_name="task",
            index=models.Index(fields=["slug"], name="tasks_task_slug_7a6a80_idx"),
        ),
        migrations.AddIndex(
            model_name="taskasset",
            index=models.Index(fields=["task", "asset_type"], name="tasks_taska_task_id_74c0f2_idx"),
        ),
    ]
