from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.db.models import Max

from apps.progress.models import HintUsage, TaskAttempt, TaskCompletion
from apps.sandbox.models import SandboxSession
from apps.tasks.models import Task, TaskAsset
from apps.users.models import PointLedgerEntry, UserProfile

from .sandbox_ops import _is_docker_session, _write_log


def validate_task(user: User, task: Task, session: SandboxSession) -> TaskAttempt:
    started = time.perf_counter()
    diagnostics = []

    validator_asset = (
        TaskAsset.objects.filter(task=task, asset_type=TaskAsset.AssetType.VALIDATOR)
        .order_by("sort_order")
        .first()
    )
    validator_path = Path(session.repo_path) / "validator.py"
    if validator_asset and validator_asset.content.strip():
        validator_path.write_text(validator_asset.content, encoding="utf-8")

    verdict = TaskAttempt.Verdict.FAILED
    try:
        if _is_docker_session(session):
            last_code = 1
            last_output = ""
            for py in ("python3", "python"):
                proc = subprocess.run(
                    ["docker", "exec", session.container_id, py, validator_path.name],
                    cwd=session.repo_path,
                    capture_output=True,
                    text=True,
                    timeout=session.timeout_seconds,
                    check=False,
                )
                last_output = (proc.stdout or "") + (proc.stderr or "")
                last_code = proc.returncode
                if last_code == 0:
                    break
            diagnostics.append(last_output or f"Command exit code: {last_code}")
            verdict = TaskAttempt.Verdict.PASSED if last_code == 0 else TaskAttempt.Verdict.FAILED
        else:
            proc = subprocess.run(
                [sys.executable, validator_path.name],
                cwd=session.repo_path,
                capture_output=True,
                text=True,
                timeout=session.timeout_seconds,
                check=False,
            )
            output = (proc.stdout or "") + (proc.stderr or "")
            _write_log(
                session,
                f"{Path(sys.executable).name} {validator_path.name}",
                output or "(no output)",
                include_in_user_log=False,
            )
            diagnostics.append(output or f"Command exit code: {proc.returncode}")
            verdict = TaskAttempt.Verdict.PASSED if proc.returncode == 0 else TaskAttempt.Verdict.FAILED
    except subprocess.TimeoutExpired:
        diagnostics.append("Validation timed out.")
        verdict = TaskAttempt.Verdict.ERROR
    except Exception as exc:  # noqa: BLE001
        diagnostics.append(f"Validation error: {exc}")
        verdict = TaskAttempt.Verdict.ERROR

    duration_ms = int((time.perf_counter() - started) * 1000)
    with transaction.atomic():
        # Сериализация нумерации попыток для одного пользователя (без удержания блокировки на время валидатора).
        User.objects.select_for_update().filter(pk=user.pk).get()
        next_attempt_no = (
            TaskAttempt.objects.filter(user=user, task=task).aggregate(m=Max("attempt_no")).get("m") or 0
        ) + 1
        attempt = TaskAttempt.objects.create(
            user=user,
            task=task,
            attempt_no=next_attempt_no,
            verdict=verdict,
            diagnostics="\n".join([x for x in diagnostics if x]).strip(),
            duration_ms=duration_ms,
        )
        if verdict == TaskAttempt.Verdict.PASSED:
            completion, created = TaskCompletion.objects.get_or_create(
                user=user,
                task=task,
                defaults={"points_awarded": task.points},
            )
            if created:
                profile, _ = UserProfile.objects.get_or_create(
                    user=user,
                    defaults={"public_nickname": user.username},
                )
                profile.total_points += completion.points_awarded
                profile.save(update_fields=["total_points", "updated_at"])
                PointLedgerEntry.objects.get_or_create(
                    user=user,
                    source=PointLedgerEntry.Source.TASK_COMPLETION,
                    ref_key=f"task:{task.id}",
                    defaults={"delta": completion.points_awarded},
                )
    return attempt


def get_next_unlockable_task_for_user(user: User) -> Task | None:
    completed = set(TaskCompletion.objects.filter(user=user).values_list("task_id", flat=True))
    for task in Task.objects.select_related("level").order_by("level__number", "order"):
        if task.id not in completed:
            return task
    return None


def can_open_task(user: User, task: Task) -> bool:
    next_task = get_next_unlockable_task_for_user(user)
    if next_task is None:
        return True
    if task.id == next_task.id:
        return True
    return TaskCompletion.objects.filter(user=user, task=task).exists()


# Стоимость подсказки по порядковому номеру (1 — первая в списке ассетов и т.д.).
HINT_UNLOCK_COSTS: dict[int, int] = {1: 3, 2: 5, 3: 10}


class NotEnoughPointsError(Exception):
    pass


def unlock_hint(user: User, task: Task, hint_index: int) -> tuple[HintUsage, int, bool]:
    """Возвращает (запись использования, списано баллов в ЭТОМ запросе, уже была открыта ранее)."""
    cost = HINT_UNLOCK_COSTS.get(hint_index, 10)
    existing = HintUsage.objects.filter(user=user, task=task, hint_index=hint_index).first()
    if existing:
        return existing, 0, True

    with transaction.atomic():
        profile = UserProfile.objects.select_for_update().filter(user=user).first()
        if profile is None:
            profile = UserProfile.objects.create(user=user, public_nickname=user.username)
        if cost > 0 and profile.total_points < cost:
            raise NotEnoughPointsError("Недостаточно баллов для покупки подсказки.")
        try:
            usage = HintUsage.objects.create(
                user=user,
                task=task,
                hint_index=hint_index,
                points_spent=cost,
            )
        except IntegrityError:
            usage = HintUsage.objects.get(user=user, task=task, hint_index=hint_index)
            return usage, 0, True
        if cost > 0:
            profile.total_points -= cost
            profile.save(update_fields=["total_points", "updated_at"])
            PointLedgerEntry.objects.get_or_create(
                user=user,
                source=PointLedgerEntry.Source.HINT,
                ref_key=f"hint:{task.id}:{hint_index}",
                defaults={"delta": -cost},
            )
    return usage, cost, False
