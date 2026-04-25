from django.db import models
from django.db.models import Q


class Level(models.Model):
    number = models.PositiveSmallIntegerField(unique=True)
    title = models.CharField(max_length=128)
    slug = models.SlugField(max_length=64, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["number"]
        constraints = [
            models.CheckConstraint(
                condition=Q(number__gte=1) & Q(number__lte=8),
                name="tasks_level_number_1_8",
            ),
        ]

    def __str__(self) -> str:
        return f"Level {self.number}: {self.title}"


class TheoryBlock(models.Model):
    level = models.OneToOneField(Level, on_delete=models.CASCADE, related_name="theory")
    title = models.CharField(max_length=128)
    content_md = models.TextField()
    diagram_mermaid = models.TextField(blank=True)
    sandbox_preset = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["level__number"]

    def __str__(self) -> str:
        return self.title


class Task(models.Model):
    class Platform(models.TextChoices):
        GITHUB = "github", "GitHub"
        GITLAB = "gitlab", "GitLab"

    external_id = models.CharField(max_length=64, unique=True)
    slug = models.SlugField(max_length=80, unique=True)
    title = models.CharField(max_length=150)
    description = models.TextField()
    platform = models.CharField(max_length=10, choices=Platform.choices, default=Platform.GITHUB)
    level = models.ForeignKey(Level, on_delete=models.PROTECT, related_name="tasks")
    order = models.PositiveSmallIntegerField()
    points = models.PositiveSmallIntegerField()
    validator_cmd = models.CharField(max_length=255, default="python validator.py")
    success_message = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["level__number", "platform", "order", "id"]
        constraints = [
            models.UniqueConstraint(fields=("level", "platform", "order"), name="tasks_unique_level_platform_order"),
            models.CheckConstraint(condition=Q(points__gte=1), name="tasks_points_positive"),
            models.CheckConstraint(condition=Q(order__gte=1), name="tasks_order_positive"),
        ]
        indexes = [
            models.Index(fields=["level", "platform", "order"]),
            models.Index(fields=["slug"]),
            models.Index(fields=["platform"]),
        ]

    def __str__(self) -> str:
        return f"{self.external_id} ({self.points} pts)"


class TaskAsset(models.Model):
    class AssetType(models.TextChoices):
        MANIFEST = "manifest", "Manifest"
        START_REPO = "start_repo", "Start repository"
        VALIDATOR = "validator", "Validator"
        HINT = "hint", "Hint"
        THEORY = "theory", "Theory"

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="assets")
    asset_type = models.CharField(max_length=20, choices=AssetType.choices)
    path = models.CharField(max_length=255)
    content = models.TextField(blank=True)
    sort_order = models.PositiveSmallIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["task__level__number", "task__order", "sort_order", "id"]
        constraints = [
            models.CheckConstraint(condition=Q(sort_order__gte=1), name="tasks_asset_order_positive"),
        ]
        indexes = [
            models.Index(fields=["task", "asset_type"]),
        ]

    def __str__(self) -> str:
        return f"{self.task.external_id}:{self.asset_type}:{self.path}"


class TaskRevision(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="revisions")
    version = models.PositiveSmallIntegerField()
    is_active = models.BooleanField(default=True)
    objective = models.TextField()
    steps = models.JSONField(default=list, blank=True)
    expected_state = models.TextField(blank=True)
    validator_notes = models.TextField(blank=True)
    schema_version = models.PositiveSmallIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["task__level__number", "task__order", "-version", "id"]
        constraints = [
            models.UniqueConstraint(fields=("task", "version"), name="tasks_revision_unique_task_version"),
            models.UniqueConstraint(
                fields=("task",),
                condition=Q(is_active=True),
                name="tasks_revision_one_active_per_task",
            ),
            models.CheckConstraint(condition=Q(version__gte=1), name="tasks_revision_version_positive"),
        ]
        indexes = [
            models.Index(fields=["task", "is_active"]),
        ]

    def __str__(self) -> str:
        status = "active" if self.is_active else "inactive"
        return f"{self.task.external_id}:v{self.version}:{status}"


class TaskCheckpoint(models.Model):
    revision = models.ForeignKey(TaskRevision, on_delete=models.CASCADE, related_name="checkpoints")
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    order = models.PositiveSmallIntegerField(default=1)
    mapping_key = models.CharField(max_length=120, blank=True, default="")
    command_hint = models.CharField(max_length=255, blank=True)
    success_criteria = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["revision__task__level__number", "revision__task__order", "order", "id"]
        constraints = [
            models.UniqueConstraint(fields=("revision", "order"), name="tasks_checkpoint_unique_revision_order"),
            models.CheckConstraint(condition=Q(order__gte=1), name="tasks_checkpoint_order_positive"),
        ]
        indexes = [
            models.Index(fields=["revision", "order"]),
        ]

    def __str__(self) -> str:
        return f"{self.revision.task.external_id}:v{self.revision.version}:cp{self.order}"
