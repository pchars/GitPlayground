from django.conf import settings
from django.db import models


class QuizQuestion(models.Model):
    """Один вопрос с четырьмя вариантами; correct_index — 0..3."""

    class Difficulty(models.TextChoices):
        EASY = "easy", "Легкий"
        MEDIUM = "medium", "Средний"
        HARD = "hard", "Тяжелый"

    prompt = models.TextField()
    choice_0 = models.CharField(max_length=512)
    choice_1 = models.CharField(max_length=512)
    choice_2 = models.CharField(max_length=512)
    choice_3 = models.CharField(max_length=512)
    explanation_0 = models.TextField(blank=True, default="")
    explanation_1 = models.TextField(blank=True, default="")
    explanation_2 = models.TextField(blank=True, default="")
    explanation_3 = models.TextField(blank=True, default="")
    correct_index = models.PositiveSmallIntegerField()
    difficulty = models.CharField(
        max_length=10,
        choices=Difficulty.choices,
        default=Difficulty.MEDIUM,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(correct_index__gte=0) & models.Q(correct_index__lte=3),
                name="quiz_correct_index_range",
            ),
        ]

    def __str__(self) -> str:
        return self.prompt[:80]


class QuizUserStats(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="quiz_stats",
    )
    answered_total = models.PositiveIntegerField(default=0)
    correct_total = models.PositiveIntegerField(default=0)
    current_streak = models.PositiveIntegerField(default=0)
    best_streak = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Статистика квиза"
        verbose_name_plural = "Статистика квиза"

    def __str__(self) -> str:
        return f"{self.user_id}: {self.correct_total}/{self.answered_total}"


class QuizQuestionProgress(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="quiz_question_progress",
    )
    question = models.ForeignKey(
        QuizQuestion,
        on_delete=models.CASCADE,
        related_name="user_progress",
    )
    attempts_total = models.PositiveIntegerField(default=0)
    failed_attempts = models.PositiveIntegerField(default=0)
    solved = models.BooleanField(default=False, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "question")
        verbose_name = "Прогресс вопроса квиза"
        verbose_name_plural = "Прогресс вопросов квиза"

    def __str__(self) -> str:
        return f"{self.user_id}:{self.question_id} solved={self.solved}"
