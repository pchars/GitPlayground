"""Страница песочницы и JSON API для терминала, файлов и валидации."""

import time

from django.contrib.auth.decorators import login_required
from django.db.models import Max
from django.http import HttpRequest, HttpResponse, JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from apps.achievements.models import UserAchievement
from apps.core.playground_limits import allow_playground_action
from apps.core.services import (
    SANDBOX_TEXT_FILE_WRITE_MAX_BYTES,
    audit_playground_repo_file,
    can_open_task,
    get_or_create_active_session,
    get_next_unlockable_task_for_user,
    read_text_file_from_repo,
    reset_session,
    run_command,
    session_log,
    stop_session,
    unlock_hint,
    validate_task,
    write_text_file_to_repo,
    NotEnoughPointsError,
)
from apps.progress.models import HintUsage, TaskAttempt
from apps.sandbox.models import SandboxSession
from apps.tasks.models import Task, TaskAsset

from .helpers import (
    _hint_ui_state,
    _log_playground_event,
    _syntax_hints,
    _task_from_route,
    _task_learning_content,
    _task_recommendations,
)


@login_required
def playground(request, task_id):
    normalized_id = task_id.replace("_", ".")
    task = get_object_or_404(Task.objects.select_related("level"), external_id=normalized_id)
    if not can_open_task(request.user, task):
        next_task = get_next_unlockable_task_for_user(request.user)
        if next_task:
            return redirect("playground", task_id=next_task.external_id.replace(".", "_"))
        return redirect("tasks")
    fresh_requested = request.GET.get("fresh") == "1"
    try:
        session = None
        if fresh_requested:
            current = (
                SandboxSession.objects.filter(
                    user=request.user,
                    task=task,
                    status__in=[SandboxSession.Status.STARTING, SandboxSession.Status.ACTIVE],
                    expires_at__gt=timezone.now(),
                )
                .order_by("-last_activity_at")
                .first()
            )
            if current:
                session = reset_session(current)
        if session is None:
            session = get_or_create_active_session(request.user, task)
    except RuntimeError as exc:
        return HttpResponse(f"Sandbox is temporarily unavailable: {exc}", status=503)
    hints = list(
        TaskAsset.objects.filter(task=task, asset_type=TaskAsset.AssetType.HINT)
        .order_by("sort_order")
        .values("sort_order", "content")
    )
    return render(
        request,
        "core/playground.html",
        {
            "task": task,
            "task_route_id": task.external_id.replace(".", "_"),
            "session": session,
            "fresh_requested": fresh_requested,
            "terminal_log": session_log(session),
            "hints": hints,
            "syntax_hints": _syntax_hints(),
            "task_recommendations": _task_recommendations(task),
            "learning_content": _task_learning_content(request.user, task),
            "hint_ui_state": _hint_ui_state(request.user, task),
            "task_subtitle": (
                (task.metadata or {}).get(
                    "playground_subtitle",
                    "Режим обучения: приоритет у команд git; для подготовки файлов разрешены безопасные команды echo/touch.",
                )
                if isinstance(task.metadata, dict)
                else "Режим обучения: приоритет у команд git; для подготовки файлов разрешены безопасные команды echo/touch."
            ),
        },
    )


@login_required
@require_POST
def playground_start(request: HttpRequest, task_id: str) -> JsonResponse:
    task = _task_from_route(task_id)
    if not can_open_task(request.user, task):
        return JsonResponse({"ok": False, "message": "Task is locked"}, status=403)
    try:
        session = get_or_create_active_session(request.user, task)
    except RuntimeError as exc:
        return JsonResponse({"ok": False, "message": str(exc)}, status=503)
    return JsonResponse({"ok": True, "session_id": session.id, "status": session.status})


@login_required
@require_POST
def playground_run_command(request: HttpRequest, task_id: str) -> JsonResponse:
    started_at = time.perf_counter()
    task = _task_from_route(task_id)
    command = (request.POST.get("command") or "").strip()
    if not command:
        _log_playground_event(
            request,
            task,
            endpoint="run",
            started_at=started_at,
            status_code=400,
            ok=False,
            reason="empty_command",
        )
        return JsonResponse({"ok": False, "message": "Command is required"}, status=400)
    if not can_open_task(request.user, task):
        _log_playground_event(
            request,
            task,
            endpoint="run",
            started_at=started_at,
            status_code=403,
            ok=False,
            reason="task_locked",
        )
        return JsonResponse({"ok": False, "message": "Task is locked"}, status=403)

    if not allow_playground_action(request.user.id, task.id, "run"):
        _log_playground_event(
            request,
            task,
            endpoint="run",
            started_at=started_at,
            status_code=429,
            ok=False,
            reason="rate_limited",
        )
        return JsonResponse(
            {"ok": False, "message": "Слишком много запросов к терминалу. Подождите немного."},
            status=429,
        )

    try:
        session = get_or_create_active_session(request.user, task)
    except RuntimeError as exc:
        _log_playground_event(
            request,
            task,
            endpoint="run",
            started_at=started_at,
            status_code=503,
            ok=False,
            reason="sandbox_unavailable",
            details=str(exc),
        )
        return JsonResponse({"ok": False, "message": str(exc)}, status=503)
    result = run_command(session, command)
    response = JsonResponse(
        {
            "ok": True,
            "command": result.command,
            "return_code": result.return_code,
            "output": result.output,
            "duration_ms": result.duration_ms,
        }
    )
    _log_playground_event(
        request,
        task,
        endpoint="run",
        started_at=started_at,
        status_code=200,
        ok=True,
        command=result.command,
        return_code=result.return_code,
        sandbox_duration_ms=result.duration_ms,
    )
    return response


@login_required
@require_GET
def playground_read_file(request: HttpRequest, task_id: str) -> JsonResponse:
    task = _task_from_route(task_id)
    if not can_open_task(request.user, task):
        return JsonResponse({"ok": False, "message": "Task is locked"}, status=403)
    if not allow_playground_action(request.user.id, task.id, "file_read"):
        return JsonResponse(
            {"ok": False, "message": "Слишком много запросов чтения файлов. Подождите немного."},
            status=429,
        )
    try:
        session = get_or_create_active_session(request.user, task)
    except RuntimeError as exc:
        return JsonResponse({"ok": False, "message": str(exc)}, status=503)
    path = (request.GET.get("path") or "").strip()
    if not path:
        return JsonResponse({"ok": False, "message": "path is required"}, status=400)
    ok, payload, truncated = read_text_file_from_repo(session, path)
    audit_playground_repo_file(
        session,
        "read",
        path,
        allowed=ok,
        extra={"truncated": truncated},
    )
    if not ok:
        return JsonResponse({"ok": False, "message": payload}, status=400)
    return JsonResponse({"ok": True, "content": payload, "truncated": truncated})


@login_required
@require_POST
def playground_write_file(request: HttpRequest, task_id: str) -> JsonResponse:
    task = _task_from_route(task_id)
    if not can_open_task(request.user, task):
        return JsonResponse({"ok": False, "message": "Task is locked"}, status=403)
    if not allow_playground_action(request.user.id, task.id, "file_write"):
        return JsonResponse(
            {"ok": False, "message": "Слишком много запросов записи файлов. Подождите немного."},
            status=429,
        )
    try:
        session = get_or_create_active_session(request.user, task)
    except RuntimeError as exc:
        return JsonResponse({"ok": False, "message": str(exc)}, status=503)
    path = (request.POST.get("path") or "").strip()
    if not path:
        return JsonResponse({"ok": False, "message": "path is required"}, status=400)
    content = request.POST.get("content", "")
    if content is None:
        content = ""
    raw_len = len(content.encode("utf-8"))
    if raw_len > SANDBOX_TEXT_FILE_WRITE_MAX_BYTES:
        audit_playground_repo_file(
            session,
            "write",
            path,
            allowed=False,
            extra={"bytes": raw_len, "deny": "too_large"},
        )
        return JsonResponse(
            {
                "ok": False,
                "message": f"Content exceeds limit ({SANDBOX_TEXT_FILE_WRITE_MAX_BYTES} bytes).",
            },
            status=400,
        )
    ok, errmsg = write_text_file_to_repo(session, path, content)
    audit_playground_repo_file(
        session,
        "write",
        path,
        allowed=ok,
        extra={"bytes": raw_len},
    )
    if not ok:
        return JsonResponse({"ok": False, "message": errmsg}, status=400)
    return JsonResponse({"ok": True, "path": path, "bytes_written": raw_len})


@login_required
@require_POST
def playground_validate(request: HttpRequest, task_id: str) -> JsonResponse:
    started_at = time.perf_counter()
    task = _task_from_route(task_id)
    if not can_open_task(request.user, task):
        _log_playground_event(
            request,
            task,
            endpoint="validate",
            started_at=started_at,
            status_code=403,
            ok=False,
            reason="task_locked",
        )
        return JsonResponse({"ok": False, "message": "Task is locked"}, status=403)
    try:
        session = get_or_create_active_session(request.user, task)
    except RuntimeError as exc:
        _log_playground_event(
            request,
            task,
            endpoint="validate",
            started_at=started_at,
            status_code=503,
            ok=False,
            reason="sandbox_unavailable",
            details=str(exc),
        )
        return JsonResponse({"ok": False, "message": str(exc)}, status=503)
    before_achievement_ids = set(
        UserAchievement.objects.filter(user=request.user).values_list("achievement_id", flat=True)
    )
    attempt = validate_task(request.user, task, session)
    new_achievements = list(
        UserAchievement.objects.filter(user=request.user)
        .exclude(achievement_id__in=before_achievement_ids)
        .select_related("achievement")
        .order_by("-awarded_at")
    )
    awarded_payload = [
        {
            "icon": item.achievement.icon_path,
            "title": item.achievement.title,
            "description": item.achievement.description,
        }
        for item in new_achievements
    ]
    next_task = None
    if attempt.verdict == TaskAttempt.Verdict.PASSED:
        next_task = get_next_unlockable_task_for_user(request.user)
    response = JsonResponse(
        {
            "ok": True,
            "verdict": attempt.verdict,
            "diagnostics": attempt.diagnostics,
            "attempt_no": attempt.attempt_no,
            "duration_ms": attempt.duration_ms,
            "learning_content": _task_learning_content(request.user, task),
            "next_task_route_id": (
                next_task.external_id.replace(".", "_")
                if next_task and next_task.id != task.id
                else None
            ),
            "awarded_achievements": awarded_payload,
        }
    )
    _log_playground_event(
        request,
        task,
        endpoint="validate",
        started_at=started_at,
        status_code=200,
        ok=True,
        verdict=attempt.verdict,
        attempt_no=attempt.attempt_no,
    )
    return response


@login_required
@require_POST
def playground_reset(request: HttpRequest, task_id: str) -> JsonResponse:
    started_at = time.perf_counter()
    task = _task_from_route(task_id)
    try:
        session = get_or_create_active_session(request.user, task)
    except RuntimeError as exc:
        _log_playground_event(
            request,
            task,
            endpoint="reset",
            started_at=started_at,
            status_code=503,
            ok=False,
            reason="sandbox_unavailable",
            details=str(exc),
        )
        return JsonResponse({"ok": False, "message": str(exc)}, status=503)
    new_session = reset_session(session)
    response = JsonResponse(
        {
            "ok": True,
            "session_id": new_session.id,
            "status": new_session.status,
            "log": session_log(new_session),
        }
    )
    _log_playground_event(
        request,
        task,
        endpoint="reset",
        started_at=started_at,
        status_code=200,
        ok=True,
        new_session_id=new_session.id,
        new_status=new_session.status,
    )
    return response


@login_required
@require_POST
def playground_stop(request: HttpRequest, task_id: str) -> JsonResponse:
    task = _task_from_route(task_id)
    session = (
        SandboxSession.objects.filter(
            user=request.user,
            task=task,
            status__in=[SandboxSession.Status.STARTING, SandboxSession.Status.ACTIVE],
        )
        .order_by("-last_activity_at")
        .first()
    )
    if session:
        stop_session(session)
    return JsonResponse({"ok": True})


@login_required
@require_POST
def playground_hint(request: HttpRequest, task_id: str) -> JsonResponse:
    started_at = time.perf_counter()
    task = _task_from_route(task_id)
    if not can_open_task(request.user, task):
        return JsonResponse({"ok": False, "message": "Task is locked"}, status=403)
    if not allow_playground_action(request.user.id, task.id, "hint"):
        _log_playground_event(
            request,
            task,
            endpoint="hint",
            started_at=started_at,
            status_code=429,
            ok=False,
            reason="rate_limited",
        )
        return JsonResponse(
            {"ok": False, "message": "Слишком много запросов подсказок. Подождите немного."},
            status=429,
        )
    try:
        hint_index = int(request.POST.get("hint_index", "1"))
    except ValueError:
        hint_index = 1
    hints = list(
        TaskAsset.objects.filter(
            task=task,
            asset_type=TaskAsset.AssetType.HINT,
        )
        .order_by("sort_order")
        .values_list("content", flat=True)
    )
    hint = hints[hint_index - 1] if 0 < hint_index <= len(hints) else None
    if not hint:
        _log_playground_event(
            request,
            task,
            endpoint="hint",
            started_at=started_at,
            status_code=400,
            ok=False,
            hint_index=hint_index,
            hint_exhausted=True,
        )
        return JsonResponse(
            {
                "ok": False,
                "message": "Подсказки для этой задачи закончились.",
            },
            status=400,
        )

    already = HintUsage.objects.filter(user=request.user, task=task, hint_index=hint_index).exists()
    if not already and hint_index > 1:
        if not HintUsage.objects.filter(user=request.user, task=task, hint_index=hint_index - 1).exists():
            resp = JsonResponse(
                {
                    "ok": False,
                    "message": "Сначала откройте предыдущую подсказку.",
                },
                status=400,
            )
            _log_playground_event(
                request,
                task,
                endpoint="hint",
                started_at=started_at,
                status_code=400,
                ok=False,
                hint_index=hint_index,
                hint_exhausted=False,
            )
            return resp

    try:
        usage, charged, was_already = unlock_hint(request.user, task, hint_index)
    except NotEnoughPointsError as exc:
        return JsonResponse({"ok": False, "message": str(exc)}, status=400)
    max_idx = (
        HintUsage.objects.filter(user=request.user, task=task).aggregate(m=Max("hint_index")).get("m") or 0
    )
    next_hint_index = max_idx + 1
    hints_exhausted = next_hint_index > len(hints)
    response = JsonResponse(
        {
            "ok": True,
            "hint_index": usage.hint_index,
            "total_hints": len(hints),
            "points_spent": charged,
            "already_unlocked": was_already,
            "next_hint_index": next_hint_index,
            "hints_exhausted": hints_exhausted,
            "content": hint,
        }
    )
    _log_playground_event(
        request,
        task,
        endpoint="hint",
        started_at=started_at,
        status_code=200,
        ok=True,
        hint_index=usage.hint_index,
        total_hints=len(hints),
        points_spent=charged,
        hint_exhausted=False,
    )
    return response


@login_required
@require_GET
def playground_log(request: HttpRequest, task_id: str) -> HttpResponse:
    task = _task_from_route(task_id)
    try:
        session = get_or_create_active_session(request.user, task)
    except RuntimeError as exc:
        return HttpResponse(f"Sandbox is unavailable: {exc}", status=503)
    return render(
        request,
        "core/partials/terminal_log.html",
        {"terminal_log": session_log(session), "task": task},
    )


@login_required
@require_GET
def playground_log_stream(request: HttpRequest, task_id: str) -> StreamingHttpResponse:
    task = _task_from_route(task_id)
    try:
        session = get_or_create_active_session(request.user, task)
    except RuntimeError as exc:
        return StreamingHttpResponse([f"event: error\ndata: {exc}\n\n"], content_type="text/event-stream")

    def event_stream():
        previous = ""
        # Keep stream bounded; client reconnects automatically.
        for _ in range(25):
            payload = session_log(session)
            if payload != previous:
                yield f"event: log\ndata: {payload.replace(chr(10), '\\n')}\n\n"
                previous = payload
            time.sleep(1)
        yield "event: done\ndata: reconnect\n\n"

    response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
    response["Cache-Control"] = "no-cache"
    return response
