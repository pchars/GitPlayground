from django.contrib import admin
from django import forms
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import path

from .importer import TaskImportError, import_task_zip, inspect_task_zip
from .models import Level, Task, TaskAsset, TheoryBlock, TaskCheckpoint, TaskRevision


class TaskAssetInline(admin.TabularInline):
    model = TaskAsset
    extra = 0


class TaskRevisionInline(admin.TabularInline):
    model = TaskRevision
    extra = 0
    fields = ("version", "is_active", "objective", "expected_state")


class TaskUploadForm(forms.Form):
    archive = forms.FileField(help_text="Upload ZIP containing task folder and manifest.yaml")


@admin.register(Level)
class LevelAdmin(admin.ModelAdmin):
    list_display = ("number", "title", "slug", "is_active")
    list_filter = ("is_active",)
    search_fields = ("title", "slug")
    ordering = ("number",)


@admin.register(TheoryBlock)
class TheoryBlockAdmin(admin.ModelAdmin):
    list_display = ("title", "level", "updated_at")
    search_fields = ("title", "level__title", "level__slug")
    list_select_related = ("level",)


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("external_id", "title", "level", "order", "points")
    list_filter = ("level",)
    list_select_related = ("level",)
    search_fields = ("external_id", "slug", "title")
    ordering = ("level__number", "order")
    inlines = [TaskAssetInline, TaskRevisionInline]

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "upload/",
                self.admin_site.admin_view(self.upload_task_zip),
                name="tasks_task_upload",
            ),
        ]
        return custom_urls + urls

    def upload_task_zip(self, request: HttpRequest) -> HttpResponse:
        form = TaskUploadForm(request.POST or None, request.FILES or None)
        context = dict(self.admin_site.each_context(request), form=form, title="Upload task ZIP")
        if request.method == "POST" and form.is_valid():
            uploaded = form.cleaned_data["archive"].read()
            action = request.POST.get("action", "preview")
            try:
                if action == "preview":
                    preview = inspect_task_zip(uploaded)
                    context["preview"] = preview
                    context["is_dry_run"] = True
                else:
                    result = import_task_zip(uploaded)
                    self.message_user(
                        request,
                        f"Task {result.task.external_id} imported with {result.imported_assets} assets.",
                    )
                    return redirect("admin:tasks_task_changelist")
            except TaskImportError as exc:
                form.add_error("archive", str(exc))
        return render(request, "admin/tasks/upload_task.html", context)


@admin.register(TaskAsset)
class TaskAssetAdmin(admin.ModelAdmin):
    list_display = ("task", "asset_type", "path", "sort_order")
    list_filter = ("asset_type", "task__level")
    search_fields = ("task__external_id", "path", "content")
    list_select_related = ("task", "task__level")


class TaskCheckpointInline(admin.TabularInline):
    model = TaskCheckpoint
    extra = 0


@admin.register(TaskRevision)
class TaskRevisionAdmin(admin.ModelAdmin):
    list_display = ("task", "version", "is_active", "schema_version", "updated_at")
    list_filter = ("is_active", "schema_version", "task__level")
    search_fields = ("task__external_id", "task__title", "objective")
    list_select_related = ("task", "task__level")
    inlines = [TaskCheckpointInline]


@admin.register(TaskCheckpoint)
class TaskCheckpointAdmin(admin.ModelAdmin):
    list_display = ("revision", "order", "title", "command_hint")
    list_filter = ("revision__task__level",)
    search_fields = ("revision__task__external_id", "title", "command_hint", "success_criteria")
    list_select_related = ("revision", "revision__task", "revision__task__level")
