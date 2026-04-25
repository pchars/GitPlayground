import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="PointLedgerEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("delta", models.IntegerField()),
                ("source", models.CharField(choices=[("task_completion", "Задача"), ("hint", "Подсказка"), ("achievement", "Достижение")], max_length=32)),
                ("ref_key", models.CharField(max_length=160)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="point_ledger_entries",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="pointledgerentry",
            constraint=models.UniqueConstraint(
                fields=("user", "source", "ref_key"),
                name="users_pointledgerentry_unique_user_source_ref",
            ),
        ),
        migrations.AddIndex(
            model_name="pointledgerentry",
            index=models.Index(fields=["user", "created_at"], name="users_point_user_id_531882_idx"),
        ),
    ]
