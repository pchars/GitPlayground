from django.conf import settings
from django.db import models
from django.db.models import Q


class TaskAttempt(models.Model):
    class Verdict(models.TextChoices):
        FAILED = "failed", "Failed"
        PASSED = "passed", "Passed"
        ERROR = "error", "Error"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="task_attempts",
    )
    task = models.ForeignKey(
        "tasks.Task",
        on_delete=models.CASCADE,
        related_name="attempts",
    )
    attempt_no = models.PositiveIntegerField(default=1)
    verdict = models.CharField(max_length=10, choices=Verdict.choices, default=Verdict.FAILED)
    diagnostics = models.TextField(blank=True)
    duration_ms = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=("user", "task", "attempt_no"),
                name="progress_unique_attempt_number",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "task", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.user_id}:{self.task_id}:{self.attempt_no}:{self.verdict}"


class TaskCompletion(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="completed_tasks",
    )
    task = models.ForeignKey(
        "tasks.Task",
        on_delete=models.CASCADE,
        related_name="completions",
    )
    points_awarded = models.PositiveSmallIntegerField(default=0)
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-completed_at"]
        constraints = [
            models.UniqueConstraint(fields=("user", "task"), name="progress_unique_completion"),
            models.CheckConstraint(
                condition=Q(points_awarded__gte=0),
                name="progress_points_awarded_non_negative",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "-completed_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.user_id}:{self.task_id}:{self.points_awarded}"


class HintUsage(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="hint_usages",
    )
    task = models.ForeignKey(
        "tasks.Task",
        on_delete=models.CASCADE,
        related_name="hint_usages",
    )
    hint_index = models.PositiveSmallIntegerField()
    points_spent = models.PositiveSmallIntegerField(default=0)
    unlocked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-unlocked_at"]
        constraints = [
            models.UniqueConstraint(
                fields=("user", "task", "hint_index"),
                name="progress_unique_hint_usage",
            ),
            models.CheckConstraint(condition=Q(hint_index__gte=1), name="progress_hint_index_positive"),
        ]
        indexes = [models.Index(fields=["user", "task"])]

    def __str__(self) -> str:
        return f"{self.user_id}:{self.task_id}:hint{self.hint_index}"


class LeaderboardSnapshot(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="leaderboard_snapshots",
    )
    total_points = models.PositiveIntegerField(default=0)
    rank = models.PositiveIntegerField(default=1)
    captured_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["captured_at", "rank"]
        constraints = [
            models.CheckConstraint(condition=Q(rank__gte=1), name="progress_rank_positive"),
        ]
        indexes = [
            models.Index(fields=["captured_at", "rank"]),
        ]

    def __str__(self) -> str:
        return f"{self.captured_at:%Y-%m-%d %H:%M} #{self.rank}"


class TaskRevisionProgress(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="task_revision_progress",
    )
    task = models.ForeignKey(
        "tasks.Task",
        on_delete=models.CASCADE,
        related_name="revision_progress",
    )
    revision = models.ForeignKey(
        "tasks.TaskRevision",
        on_delete=models.CASCADE,
        related_name="user_progress",
    )
    is_current = models.BooleanField(default=True)
    migrated_from_revision = models.ForeignKey(
        "tasks.TaskRevision",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="migrated_to_progress",
    )
    completion_pct = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=("user", "task", "revision"),
                name="progress_unique_user_task_revision_progress",
            ),
            models.UniqueConstraint(
                fields=("user", "task"),
                condition=Q(is_current=True),
                name="progress_single_current_revision_progress",
            ),
            models.CheckConstraint(
                condition=Q(completion_pct__gte=0) & Q(completion_pct__lte=100),
                name="progress_revision_completion_pct_range",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "task", "is_current"]),
        ]

    def __str__(self) -> str:
        return f"{self.user_id}:{self.task_id}:rev{self.revision_id}:{self.completion_pct}%"


class CheckpointProgress(models.Model):
    class Status(models.TextChoices):
        LOCKED = "locked", "Locked"
        IN_PROGRESS = "in_progress", "In progress"
        DONE = "done", "Done"

    revision_progress = models.ForeignKey(
        TaskRevisionProgress,
        on_delete=models.CASCADE,
        related_name="checkpoints",
    )
    checkpoint = models.ForeignKey(
        "tasks.TaskCheckpoint",
        on_delete=models.CASCADE,
        related_name="user_progress",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.LOCKED)
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["checkpoint__order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=("revision_progress", "checkpoint"),
                name="progress_unique_checkpoint_progress",
            ),
        ]
        indexes = [
            models.Index(fields=["revision_progress", "status"]),
        ]

    def __str__(self) -> str:
        return f"rp{self.revision_progress_id}:cp{self.checkpoint_id}:{self.status}"
