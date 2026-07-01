"""Общие вспомогательные функции для представлений core (playground, learning UI)."""

import json
import logging
import time

from django.contrib.auth.models import User
from django.http import HttpRequest
from django.shortcuts import get_object_or_404

from apps.progress.models import HintUsage, TaskRevisionProgress
from apps.tasks.models import Task, TaskAsset

playground_logger = logging.getLogger("apps.core.playground")


def _get_request_id(request: HttpRequest) -> str:
    return getattr(request, "request_id", "") or request.META.get("HTTP_X_REQUEST_ID", "")


def _log_playground_event(
    request: HttpRequest,
    task: Task,
    endpoint: str,
    started_at: float,
    status_code: int,
    **extra,
) -> None:
    payload = {
        "event": "playground_api",
        "endpoint": endpoint,
        "request_id": _get_request_id(request),
        "user_id": request.user.id if request.user.is_authenticated else None,
        "task_id": task.id,
        "task_external_id": task.external_id,
        "task_level": task.level.number,
        "status_code": status_code,
        "status_family": f"{status_code // 100}xx",
        "outcome": "success" if status_code < 400 else "error",
        "latency_ms": int((time.perf_counter() - started_at) * 1000),
    }
    if extra:
        payload.update(extra)
    playground_logger.info(json.dumps(payload, ensure_ascii=False))


def _ensure_revision_progress(user: User, task: Task) -> TaskRevisionProgress | None:
    """Текущий прогресс по активной ревизии задачи (без чек-листа по шагам)."""
    active_revision = task.revisions.filter(is_active=True).order_by("-version").first()
    if not active_revision:
        return None

    current = (
        TaskRevisionProgress.objects.filter(user=user, task=task, is_current=True)
        .select_related("revision")
        .first()
    )
    if current and current.revision_id == active_revision.id:
        return current

    if current:
        current.is_current = False
        current.save(update_fields=["is_current", "updated_at"])

    progress, created = TaskRevisionProgress.objects.get_or_create(
        user=user,
        task=task,
        revision=active_revision,
        defaults={
            "is_current": True,
            "migrated_from_revision": current.revision if current else None,
            "completion_pct": 0,
        },
    )
    if not created and not progress.is_current:
        progress.is_current = True
        progress.save(update_fields=["is_current", "updated_at"])
    return progress


def _task_learning_content(user: User, task: Task) -> dict:
    revision = task.revisions.filter(is_active=True).order_by("-version").first()
    _ensure_revision_progress(user, task)
    if not revision:
        return {
            "objective": task.description,
            "steps": [],
            "expected_state": "",
            "validator_notes": "",
            "version": None,
        }
    return {
        "objective": revision.objective,
        "steps": revision.steps or [],
        "expected_state": revision.expected_state,
        "validator_notes": revision.validator_notes,
        "version": revision.version,
    }


def _hint_ui_state(user: User, task: Task) -> dict:
    """Состояние подсказок для плейграунда: уже открытые, следующий индекс, исчерпан ли лимит."""
    contents = list(
        TaskAsset.objects.filter(task=task, asset_type=TaskAsset.AssetType.HINT)
        .order_by("sort_order")
        .values_list("content", flat=True)
    )
    total = len(contents)
    rows = list(
        HintUsage.objects.filter(user=user, task=task).order_by("hint_index").values("hint_index", "points_spent")
    )
    revealed: list[dict] = []
    for row in rows:
        idx = row["hint_index"]
        if 1 <= idx <= total:
            revealed.append(
                {
                    "index": idx,
                    "content": contents[idx - 1],
                    "points_spent": row["points_spent"],
                }
            )
    max_idx = max((r["hint_index"] for r in rows), default=0)
    next_hint_index = max_idx + 1 if total else 1
    exhausted = total == 0 or max_idx >= total
    return {
        "revealed": revealed,
        "next_hint_index": next_hint_index,
        "exhausted": exhausted,
        "total": total,
    }


def _task_from_route(task_id: str) -> Task:
    return get_object_or_404(Task.objects.select_related("level"), external_id=task_id.replace("_", "."))
