from django.conf import settings
from django.db import models

from apps.users.validators import validate_pseudonym


class UserProfile(models.Model):
    class LearningGoal(models.TextChoices):
        INTERVIEW = "interview", "Подготовка к собеседованию"
        WORK = "work", "Для работы"
        PROJECT = "project", "Pet-проект / своё"
        INTEREST = "interest", "Просто интересно"

    class KnowledgeLevel(models.TextChoices):
        NONE = "none", "Не пользовался"
        BASIC = "basic", "Базовый"
        CONFIDENT = "confident", "Уверенный"
        ADVANCED = "advanced", "Продвинутый"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    pseudonym = models.CharField(max_length=10, unique=True, validators=[validate_pseudonym])
    certificate_name = models.CharField(max_length=120)
    learning_goal = models.CharField(max_length=32, choices=LearningGoal.choices)
    knowledge_level = models.CharField(max_length=32, choices=KnowledgeLevel.choices)
    job_role = models.CharField(max_length=120, blank=True, default="")
    company_name = models.CharField(max_length=160, blank=True, default="")
    total_points = models.PositiveIntegerField(default=0)
    marketing_opt_in = models.BooleanField(default=False)
    marketing_consent_at = models.DateTimeField(null=True, blank=True)
    marketing_consent_version = models.CharField(max_length=32, blank=True, default="")
    marketing_consent_text = models.TextField(blank=True, default="")
    privacy_consent_at = models.DateTimeField()
    privacy_consent_version = models.CharField(max_length=32)
    privacy_consent_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-total_points", "pseudonym"]

    def __str__(self) -> str:
        return self.pseudonym

    def get_learning_goal_display_ru(self) -> str:
        return self.get_learning_goal_display()

    def get_knowledge_level_display_ru(self) -> str:
        return self.get_knowledge_level_display()


class PointLedgerEntry(models.Model):
    """Points change ledger (source of truth to reconcile UserProfile.total_points)."""

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
