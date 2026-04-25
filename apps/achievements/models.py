from django.conf import settings
from django.db import models


class Achievement(models.Model):
    """Достижение; критерий выдачи задаётся полями criterion_* (threshold_tasks остаётся для совместимости UI)."""

    class CriterionKind(models.TextChoices):
        TASKS_COMPLETED = "tasks_completed", "Завершённые задачи"
        QUIZ_EASY_SOLVED = "quiz_easy_solved", "Квиз: лёгкие"
        QUIZ_MEDIUM_SOLVED = "quiz_medium_solved", "Квиз: средние"
        QUIZ_HARD_SOLVED = "quiz_hard_solved", "Квиз: сложные"
        QUIZ_ALL_SOLVED = "quiz_all_solved", "Квиз: все вопросы"
        STREAK_MIN = "streak_min", "Серия ответов"
        STREAK_FLAWLESS = "streak_flawless", "Квиз без ошибок"

    slug = models.SlugField(max_length=80, unique=True)
    title = models.CharField(max_length=120)
    description = models.TextField()
    icon_path = models.CharField(max_length=255, blank=True, default="")
    points_bonus = models.PositiveSmallIntegerField(default=0)
    threshold_tasks = models.PositiveSmallIntegerField(default=0)
    criterion_kind = models.CharField(
        max_length=32,
        choices=CriterionKind.choices,
        default=CriterionKind.TASKS_COMPLETED,
    )
    criterion_target = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["title"]

    def __str__(self) -> str:
        return self.title


class UserAchievement(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="achievements",
    )
    achievement = models.ForeignKey(
        Achievement,
        on_delete=models.CASCADE,
        related_name="users",
    )
    awarded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-awarded_at"]
        constraints = [
            models.UniqueConstraint(
                fields=("user", "achievement"),
                name="achievements_unique_user_achievement",
            ),
        ]
        indexes = [models.Index(fields=["user", "awarded_at"])]

    def __str__(self) -> str:
        return f"{self.user_id}:{self.achievement.slug}"
