from django.contrib import admin

from .models import SandboxSession


@admin.register(SandboxSession)
class SandboxSessionAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "task",
        "container_id",
        "status",
        "timeout_seconds",
        "expires_at",
    )
    list_filter = ("status", "task__level")
    search_fields = ("container_id", "user__username", "user__email", "repo_path")
    list_select_related = ("user", "task", "task__level")
