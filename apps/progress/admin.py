from django.contrib import admin

from .models import (
    CheckpointProgress,
    HintUsage,
    LeaderboardSnapshot,
    TaskAttempt,
    TaskCompletion,
    TaskRevisionProgress,
)


@admin.register(TaskAttempt)
class TaskAttemptAdmin(admin.ModelAdmin):
    list_display = ("user", "task", "attempt_no", "verdict", "duration_ms", "created_at")
    list_filter = ("verdict", "task__level")
    search_fields = ("user__username", "user__email", "task__external_id")
    list_select_related = ("user", "task", "task__level")


@admin.register(TaskCompletion)
class TaskCompletionAdmin(admin.ModelAdmin):
    list_display = ("user", "task", "points_awarded", "completed_at")
    list_filter = ("task__level",)
    search_fields = ("user__username", "task__external_id")
    list_select_related = ("user", "task", "task__level")


@admin.register(HintUsage)
class HintUsageAdmin(admin.ModelAdmin):
    list_display = ("user", "task", "hint_index", "points_spent", "unlocked_at")
    list_filter = ("task__level",)
    search_fields = ("user__username", "task__external_id")
    list_select_related = ("user", "task", "task__level")


@admin.register(LeaderboardSnapshot)
class LeaderboardSnapshotAdmin(admin.ModelAdmin):
    list_display = ("captured_at", "rank", "user", "total_points")
    list_filter = ("captured_at",)
    search_fields = ("user__username", "user__email")
    list_select_related = ("user",)


@admin.register(TaskRevisionProgress)
class TaskRevisionProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "task", "revision", "is_current", "completion_pct", "updated_at")
    list_filter = ("is_current", "task__level")
    search_fields = ("user__username", "task__external_id")
    list_select_related = ("user", "task", "task__level", "revision")


@admin.register(CheckpointProgress)
class CheckpointProgressAdmin(admin.ModelAdmin):
    list_display = ("revision_progress", "checkpoint", "status", "completed_at", "updated_at")
    list_filter = ("status", "checkpoint__revision__task__level")
    search_fields = ("revision_progress__user__username", "checkpoint__revision__task__external_id")
    list_select_related = (
        "revision_progress",
        "revision_progress__user",
        "checkpoint",
        "checkpoint__revision",
        "checkpoint__revision__task",
    )
