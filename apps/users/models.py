from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    public_nickname = models.CharField(max_length=64, unique=True)
    total_points = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-total_points", "public_nickname"]

    def __str__(self) -> str:
        return self.public_nickname


class PointLedgerEntry(models.Model):
    """Журнал изменений баллов (источник правды для сверки с UserProfile.total_points)."""

    class Source(models.TextChoices):
        TASK_COMPLETION = "task_completion", "Задача"
        HINT = "hint", "Подсказка"
        ACHIEVEMENT = "achievement", "Достижение"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="point_ledger_entries",
    )
    delta = models.IntegerField()
    source = models.CharField(max_length=32, choices=Source.choices)
    ref_key = models.CharField(max_length=160)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=("user", "source", "ref_key"),
                name="users_pointledgerentry_unique_user_source_ref",
            ),
        ]
        indexes = [models.Index(fields=["user", "created_at"])]

    def __str__(self) -> str:
        return f"{self.user_id}:{self.source}:{self.ref_key}:{self.delta}"
