from django.db import migrations, models


def backfill_criteria(apps, schema_editor):
    Achievement = apps.get_model("achievements", "Achievement")
    for ach in Achievement.objects.all():
        slug = ach.slug
        if slug == "quiz_easy_complete":
            kind = "quiz_easy_solved"
        elif slug == "quiz_medium_complete":
            kind = "quiz_medium_solved"
        elif slug == "quiz_hard_complete":
            kind = "quiz_hard_solved"
        elif slug == "quiz_all_complete":
            kind = "quiz_all_solved"
        elif slug == "streak_flawless":
            kind = "streak_flawless"
        elif slug.startswith("streak_"):
            kind = "streak_min"
        else:
            kind = "tasks_completed"
        ach.criterion_kind = kind
        ach.criterion_target = ach.threshold_tasks
        ach.save(update_fields=["criterion_kind", "criterion_target"])


class Migration(migrations.Migration):

    dependencies = [
        ("achievements", "0003_rename_achievement_user_id_179db8_idx_achievement_user_id_4ac750_idx_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="achievement",
            name="criterion_kind",
            field=models.CharField(
                choices=[
                    ("tasks_completed", "Завершённые задачи"),
                    ("quiz_easy_solved", "Квиз: лёгкие"),
                    ("quiz_medium_solved", "Квиз: средние"),
                    ("quiz_hard_solved", "Квиз: сложные"),
                    ("quiz_all_solved", "Квиз: все вопросы"),
                    ("streak_min", "Серия ответов"),
                    ("streak_flawless", "Квиз без ошибок"),
                ],
                default="tasks_completed",
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="achievement",
            name="criterion_target",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.RunPython(backfill_criteria, migrations.RunPython.noop),
    ]
