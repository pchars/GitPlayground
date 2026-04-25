"""Общие вспомогательные функции для представлений core (playground, learning UI)."""

from functools import lru_cache
import json
import logging
import time

from django.contrib.auth.models import User
from django.db import connection
from django.db.utils import DatabaseError
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


def _syntax_hints() -> list[dict[str, str]]:
    return [
        {
            "command": "git add",
            "syntax": "git add <file> | git add . | git add -p",
            "example": "git add hello.txt",
            "description": "Добавляет изменения в индекс перед коммитом.",
        },
        {
            "command": "git commit",
            "syntax": 'git commit -m "<message>" | git commit --amend',
            "example": 'git commit -m "Add hello"',
            "description": "Создает фиксацию из текущего индекса.",
        },
        {
            "command": "git log",
            "syntax": "git log --oneline --graph --decorate -n 10",
            "example": "git log --oneline --graph",
            "description": "Показывает историю коммитов и структуру веток.",
        },
        {
            "command": "git status",
            "syntax": "git status | git status --short",
            "example": "git status --short",
            "description": "Показывает состояние рабочей директории и индекса.",
        },
        {
            "command": "cat",
            "syntax": "cat <file> (без флагов; только внутри ~/repo)",
            "example": "cat README_TASK.txt",
            "description": "Показывает содержимое одного текстового файла.",
        },
    ]


def _task_recommendations(task: Task) -> list[str]:
    metadata = task.metadata or {}
    metadata_recommendations = metadata.get("recommendations")
    if isinstance(metadata_recommendations, list) and metadata_recommendations:
        return [str(item) for item in metadata_recommendations]

    by_slug = {
        "init_repo": [
            "Начни с git status, чтобы увидеть, что репозиторий не инициализирован.",
            "Выполни git init и повтори git status для проверки результата.",
        ],
        "first_commit": [
            "Создай файл (echo \"Hello, Git!\" > hello.txt), затем git add hello.txt.",
            "Проверь staged-изменения через git status --short перед коммитом.",
            "Используй точное сообщение: Add hello.",
        ],
        "check_status": [
            "Измени hello.txt без git add и проверь, что файл в modified (unstaged).",
            "Команда git diff покажет незастейдженные изменения.",
        ],
        "stage_unstage": [
            "Сначала добавь файл в индекс командой git add.",
            "Затем верни в unstaged через git restore --staged <file>.",
        ],
        "commit_second": [
            "Сделай осмысленное изменение файла и закоммить его как Update hello.",
            "Проверь историю через git log --oneline -n 2.",
        ],
        "view_diff": [
            "Добавь строку в файл и используй git diff до индексации.",
            "После git add сравни с git diff --cached.",
        ],
    }
    fallback = [
        "Перед действием проверь состояние: git status --short.",
        "После ключевого шага подтверждай результат через git log/git status.",
    ]
    return by_slug.get(task.slug, fallback)


@lru_cache(maxsize=8)
def _task_has_platform_column() -> bool:
    try:
        with connection.cursor() as cursor:
            columns = connection.introspection.get_table_description(cursor, Task._meta.db_table)
        return any(col.name == "platform" for col in columns)
    except DatabaseError:
        return False


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
