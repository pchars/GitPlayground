from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tasks", "0003_taskcheckpoint_mapping_key"),
    ]

    operations = [
        migrations.AddField(
            model_name="task",
            name="platform",
            field=models.CharField(
                choices=[("github", "GitHub"), ("gitlab", "GitLab")],
                default="github",
                max_length=10,
            ),
        ),
        migrations.AddIndex(
            model_name="task",
            index=models.Index(fields=["platform"], name="tasks_task_platform_0f34a9_idx"),
        ),
        migrations.RemoveConstraint(
            model_name="task",
            name="tasks_unique_level_order",
        ),
        migrations.AddConstraint(
            model_name="task",
            constraint=models.UniqueConstraint(
                fields=("level", "platform", "order"),
                name="tasks_unique_level_platform_order",
            ),
        ),
        migrations.RemoveIndex(
            model_name="task",
            name="tasks_task_level_i_8e314d_idx",
        ),
        migrations.AddIndex(
            model_name="task",
            index=models.Index(fields=["level", "platform", "order"], name="tasks_task_level_4f8d77_idx"),
        ),
    ]
