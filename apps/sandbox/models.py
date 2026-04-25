from django.conf import settings
from django.db import models
from django.db.models import Q


class SandboxSession(models.Model):
    class Status(models.TextChoices):
        STARTING = "starting", "Starting"
        ACTIVE = "active", "Active"
        STOPPED = "stopped", "Stopped"
        EXPIRED = "expired", "Expired"
        FAILED = "failed", "Failed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sandbox_sessions",
    )
    task = models.ForeignKey(
        "tasks.Task",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sandbox_sessions",
    )
    container_id = models.CharField(max_length=128, unique=True)
    repo_path = models.CharField(max_length=255)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.STARTING)
    timeout_seconds = models.PositiveSmallIntegerField(default=30)
    max_repo_size_mb = models.PositiveSmallIntegerField(default=10)
    started_at = models.DateTimeField(auto_now_add=True)
    last_activity_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ["-last_activity_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(timeout_seconds__gte=1) & Q(timeout_seconds__lte=300),
                name="sandbox_timeout_seconds_range",
            ),
            models.CheckConstraint(
                condition=Q(max_repo_size_mb__gte=1) & Q(max_repo_size_mb__lte=1024),
                name="sandbox_repo_size_mb_range",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.user_id}:{self.container_id}:{self.status}"
