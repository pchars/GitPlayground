from __future__ import annotations

import logging
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.db.models import Max

from apps.core.client_errors import VALIDATION_INTERNAL_ERROR, log_exception
from apps.progress.models import HintUsage, TaskAttempt, TaskCompletion, TaskRevisionProgress
from apps.sandbox.models import SandboxSession
from apps.tasks.models import Level, Task, TaskAsset
from apps.users.models import PointLedgerEntry, UserProfile
from apps.users.services import ensure_user_profile

from .sandbox_exec import run_sandbox_argv
from .sandbox_ops import is_docker_session, write_session_log, git_env

logger = logging.getLogger(__name__)

# Intro levels that do not gate the main Git track (level 1+).
NON_BLOCKING_LEVEL_NUMBERS: frozenset[int] = frozenset({0})


def _completed_task_ids_for_user(user: User) -> set[int]:
    return set(TaskCompletion.objects.filter(user=user).values_list("task_id", flat=True))


def _iter_github_tasks():
    return Task.objects.select_related("level").filter(platform=Task.Platform.GITHUB).order_by(
        "level__number", "order"
    )


def get_next_optional_track_task_for_user(user: User) -> Task | None:
    completed = _completed_task_ids_for_user(user)
    for task in _iter_github_tasks():
        if task.level.number not in NON_BLOCKING_LEVEL_NUMBERS:
            continue
        if task.id not in completed:
            return task
    return None


def get_next_unlockable_task_for_user(user: User) -> Task | None:
    """First incomplete task on the main track (level 1+). Level 0 never blocks."""
    completed = _completed_task_ids_for_user(user)
    for task in _iter_github_tasks():
        if task.level.number in NON_BLOCKING_LEVEL_NUMBERS:
            continue
        if task.id not in completed:
            return task
    return None


def get_suggested_next_task_after_pass(user: User, completed_task: Task) -> Task | None:
    if completed_task.level.number in NON_BLOCKING_LEVEL_NUMBERS:
        next_optional = get_next_optional_track_task_for_user(user)
        if next_optional is not None:
            return next_optional
    return get_next_unlockable_task_for_user(user)


def can_open_task(user: User, task: Task) -> bool:
    if TaskCompletion.objects.filter(user=user, task=task).exists():
        return True
    if task.level.number in NON_BLOCKING_LEVEL_NUMBERS:
        next_optional = get_next_optional_track_task_for_user(user)
        if next_optional is None:
            return True
        return task.id == next_optional.id
    next_task = get_next_unlockable_task_for_user(user)
    if next_task is None:
        return True
    return task.id == next_task.id


def build_tasks_list_context(user: User, *, selected_level: Level | None = None) -> dict:
    """Status matrix for the tasks page (completed / active / locked)."""
    from collections import defaultdict

    levels = Level.objects.prefetch_related("tasks").order_by("number")
    completed_ids = _completed_task_ids_for_user(user)
    all_tasks = list(_iter_github_tasks())
    next_main_task = get_next_unlockable_task_for_user(user)
    next_optional_task = get_next_optional_track_task_for_user(user)
    active_task_ids = {
        task.id for task in (next_main_task, next_optional_task) if task is not None
    }

    grouped: dict[int, list] = defaultdict(list)
    for task in all_tasks:
        if task.id in completed_ids:
            status = "completed"
        elif task.id in active_task_ids:
            status = "active"
        else:
            status = "locked"
        grouped[task.level.number].append(
            {
                "task": task,
                "status": status,
                "task_route_id": task.external_id.replace(".", "_"),
            }
        )

    level_rows = []
    for level in levels:
        row_tasks = grouped[level.number]
        row_total = len(row_tasks)
        row_completed = sum(1 for item in row_tasks if item["status"] == "completed")
        row_active = sum(1 for item in row_tasks if item["status"] == "active")
        row_pct = round((row_completed / row_total) * 100) if row_total else 0
        level_rows.append(
            {
                "level": level,
                "tasks": row_tasks,
                "total": row_total,
                "completed": row_completed,
                "active_count": row_active,
                "progress_pct": row_pct,
            }
        )

    total_tasks = len(all_tasks)
    completed_tasks = len(completed_ids)
    overall_pct = round((completed_tasks / total_tasks) * 100) if total_tasks else 0
    return {
        "level_rows": level_rows,
        "selected_level": selected_level,
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "overall_pct": overall_pct,
        "expanded_level_number": selected_level.number if selected_level else None,
    }


def profile_learning_stats(user: User) -> dict:
    """Aggregates for profile page: levels, achievements gallery, quiz counts."""
    from apps.achievements.models import Achievement, UserAchievement
    from apps.achievements.services import achievement_gallery_sort_key, quiz_streak_flawless_status
    from apps.quiz.models import QuizQuestion, QuizQuestionProgress, QuizUserStats

    K = Achievement.CriterionKind
    profile = ensure_user_profile(user)
    completed_task_ids = _completed_task_ids_for_user(user)
    levels = Level.objects.prefetch_related("tasks").order_by("number")
    level_progress = []
    total_tasks = 0
    total_completed = 0
    for level in levels:
        task_ids = [task.id for task in level.tasks.all()]
        completed = sum(1 for task_id in task_ids if task_id in completed_task_ids)
        level_total = len(task_ids)
        total_tasks += level_total
        total_completed += completed
        level_progress.append({"level": level, "completed": completed, "total": level_total})

    progress_pct = round((total_completed / total_tasks) * 100) if total_tasks else 0
    achievements = UserAchievement.objects.filter(user=user).select_related("achievement").order_by(
        "-awarded_at"
    )
    achievement_map = {ua.achievement_id: ua for ua in achievements}
    all_achievements = sorted(
        Achievement.objects.filter(is_active=True),
        key=achievement_gallery_sort_key,
    )
    completed_tasks_count = len(completed_task_ids)
    theory_dropoff = max(0, total_tasks - total_completed)
    quiz_stats, _ = QuizUserStats.objects.get_or_create(user=user)
    solved_progress = QuizQuestionProgress.objects.filter(user=user, solved=True).select_related(
        "question"
    )
    solved_total = solved_progress.count()
    solved_easy = solved_progress.filter(question__difficulty=QuizQuestion.Difficulty.EASY).count()
    solved_medium = solved_progress.filter(
        question__difficulty=QuizQuestion.Difficulty.MEDIUM
    ).count()
    solved_hard = solved_progress.filter(question__difficulty=QuizQuestion.Difficulty.HARD).count()
    total_quiz = QuizQuestion.objects.count()
    total_easy = QuizQuestion.objects.filter(difficulty=QuizQuestion.Difficulty.EASY).count()
    total_medium = QuizQuestion.objects.filter(difficulty=QuizQuestion.Difficulty.MEDIUM).count()
    total_hard = QuizQuestion.objects.filter(difficulty=QuizQuestion.Difficulty.HARD).count()
    available_achievements = []
    for ach in all_achievements:
        unlocked = ach.id in achievement_map
        if ach.criterion_kind == K.QUIZ_EASY_SOLVED:
            progress_text = f"{solved_easy}/{total_easy} вопросов легкого уровня"
        elif ach.criterion_kind == K.QUIZ_MEDIUM_SOLVED:
            progress_text = f"{solved_medium}/{total_medium} вопросов среднего уровня"
        elif ach.criterion_kind == K.QUIZ_HARD_SOLVED:
            progress_text = f"{solved_hard}/{total_hard} вопросов тяжелого уровня"
        elif ach.criterion_kind == K.QUIZ_ALL_SOLVED:
            progress_text = f"{solved_total}/{total_quiz} вопросов квиза"
        elif ach.criterion_kind == K.STREAK_FLAWLESS:
            progress_text = (
                f"{solved_total}/{total_quiz} вопросов, статус: {quiz_streak_flawless_status(user)}"
            )
        elif ach.criterion_kind == K.STREAK_MIN:
            progress_text = f"Лучшая серия: {quiz_stats.best_streak}/{ach.criterion_target}"
        else:
            progress_text = f"{completed_tasks_count}/{ach.criterion_target} задач"
        available_achievements.append(
            {
                "achievement": ach,
                "unlocked": unlocked,
                "progress_text": progress_text,
                "awarded_at": achievement_map.get(ach.id).awarded_at if unlocked else None,
            }
        )
    return {
        "profile": profile,
        "level_progress": level_progress,
        "total_tasks": total_tasks,
        "total_completed": total_completed,
        "progress_pct": progress_pct,
        "available_achievements": available_achievements,
        "completed_tasks_count": completed_tasks_count,
        "theory_dropoff": theory_dropoff,
        "quiz_stats": quiz_stats,
        "solved_total": solved_total,
        "total_quiz": total_quiz,
    }


def validate_task(user: User, task: Task, session: SandboxSession) -> TaskAttempt:
    started = time.perf_counter()
    diagnostics = []

    validator_asset = (
        TaskAsset.objects.filter(task=task, asset_type=TaskAsset.AssetType.VALIDATOR)
        .order_by("sort_order")
        .first()
    )
    validator_path = Path(session.repo_path) / "validator.py"
    validator_written_from_asset = False
    if validator_asset and validator_asset.content.strip():
        validator_path.write_text(validator_asset.content, encoding="utf-8")
        validator_written_from_asset = True

    verdict = TaskAttempt.Verdict.FAILED
    try:
        if is_docker_session(session):
            last_code = 1
            last_output = ""
            for py in ("python3", "python"):
                proc = run_sandbox_argv(session, [py, validator_path.name])
                last_output = (proc.stdout or "") + (proc.stderr or "")
                last_code = proc.returncode
                if last_code == 0:
                    break
            diagnostics.append(last_output or f"Command exit code: {last_code}")
            verdict = TaskAttempt.Verdict.PASSED if last_code == 0 else TaskAttempt.Verdict.FAILED
        else:
            proc = run_sandbox_argv(
                session,
                [sys.executable, validator_path.name],
                env=git_env(),
            )
            output = (proc.stdout or "") + (proc.stderr or "")
            write_session_log(
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
        log_exception(logger, "task validator failed", exc)
        diagnostics.append(VALIDATION_INTERNAL_ERROR)
        verdict = TaskAttempt.Verdict.ERROR
    finally:
        if validator_written_from_asset:
            validator_path.unlink(missing_ok=True)

    duration_ms = int((time.perf_counter() - started) * 1000)
    with transaction.atomic():
        # Serialize attempt numbering per user (no lock held during validator run).
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
                profile = ensure_user_profile(user)
                profile.total_points += completion.points_awarded
                profile.save(update_fields=["total_points", "updated_at"])
                PointLedgerEntry.objects.get_or_create(
                    user=user,
                    source=PointLedgerEntry.Source.TASK_COMPLETION,
                    ref_key=f"task:{task.id}",
                    defaults={"delta": completion.points_awarded},
                )
    return attempt


# Hint cost by unlock order (1 = first hint asset, etc.).
# Kept high vs task rewards so hints stay a deliberate spend.
HINT_UNLOCK_COSTS: dict[int, int] = {1: 5, 2: 8, 3: 12}


class NotEnoughPointsError(Exception):
    message = "Недостаточно баллов для покупки подсказки."

    def __init__(self) -> None:
        super().__init__(self.message)


class HintRequestError(Exception):
    def __init__(self, message: str, *, status_code: int = 400) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


@dataclass(frozen=True)
class HintUnlockResult:
    hint_index: int
    total_hints: int
    points_spent: int
    already_unlocked: bool
    next_hint_index: int
    hints_exhausted: bool
    content: str


def process_hint_request(user: User, task: Task, hint_index: int) -> HintUnlockResult:
    """Validate hint order, charge points, return JSON API payload."""
    hints = list(
        TaskAsset.objects.filter(task=task, asset_type=TaskAsset.AssetType.HINT)
        .order_by("sort_order")
        .values_list("content", flat=True)
    )
    hint = hints[hint_index - 1] if 0 < hint_index <= len(hints) else None
    if not hint:
        raise HintRequestError("Подсказки для этой задачи закончились.")

    already = HintUsage.objects.filter(user=user, task=task, hint_index=hint_index).exists()
    if not already and hint_index > 1:
        if not HintUsage.objects.filter(user=user, task=task, hint_index=hint_index - 1).exists():
            raise HintRequestError("Сначала откройте предыдущую подсказку.")

    usage, charged, was_already = unlock_hint(user, task, hint_index)
    max_idx = (
        HintUsage.objects.filter(user=user, task=task).aggregate(m=Max("hint_index")).get("m") or 0
    )
    next_hint_index = max_idx + 1
    hints_exhausted = next_hint_index > len(hints)
    return HintUnlockResult(
        hint_index=usage.hint_index,
        total_hints=len(hints),
        points_spent=charged,
        already_unlocked=was_already,
        next_hint_index=next_hint_index,
        hints_exhausted=hints_exhausted,
        content=hint,
    )


def unlock_hint(user: User, task: Task, hint_index: int) -> tuple[HintUsage, int, bool]:
    """Return (usage row, points spent in THIS request, already unlocked before)."""
    cost = HINT_UNLOCK_COSTS.get(hint_index, 12)
    existing = HintUsage.objects.filter(user=user, task=task, hint_index=hint_index).first()
    if existing:
        return existing, 0, True

    with transaction.atomic():
        profile = UserProfile.objects.select_for_update().filter(user=user).first()
        if profile is None:
            profile = ensure_user_profile(user)
        if cost > 0 and profile.total_points < cost:
            raise NotEnoughPointsError()
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


def ensure_revision_progress(user: User, task: Task) -> TaskRevisionProgress | None:
    """Current progress for the active task revision (no per-step checklist)."""
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


def task_learning_content(user: User, task: Task) -> dict:
    revision = task.revisions.filter(is_active=True).order_by("-version").first()
    ensure_revision_progress(user, task)
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


def hint_ui_state(user: User, task: Task) -> dict:
    """Hint state for playground: unlocked, next index, whether limit is exhausted."""
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
