"""Shared helpers for core views (playground, learning UI)."""

import json
import logging
import time

from django.http import HttpRequest
from django.shortcuts import get_object_or_404

from apps.tasks.models import Task

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


def _task_from_route(task_id: str) -> Task:
    return get_object_or_404(Task.objects.select_related("level"), external_id=task_id.replace("_", "."))
