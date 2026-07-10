from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import json
import logging
from pathlib import Path
import os
import shutil
import subprocess
import sys
import time
from uuid import uuid4

from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone

from apps.core.client_errors import (
    FILE_READ_FAILED,
    FILE_WRITE_FAILED,
    MKDIR_FAILED,
)
from apps.sandbox.models import SandboxSession
from apps.tasks.models import Task

from .command_policy import SANDBOX_ALLOWED_COMMANDS_SUMMARY, parse_user_command
from .repo_path_io import (
    append_repo_text_line,
    cp_repo_file,
    find_repo_paths,
    head_repo_file,
    list_repo_path,
    mkdir_repo_path,
    mv_repo_file,
    read_repo_file_bytes,
    restore_or_remove_repo_file,
    rm_repo_path,
    tail_repo_file,
    touch_repo_file,
    wc_repo_file,
    write_empty_repo_file,
    write_repo_file_bytes,
)
from .sandbox_git import (
    SANDBOX_ROOT,
    ensure_sandbox_root,
    git_env,
)
from .workspace_seed import seed_workspace_from_assets


SANDBOX_ENGINE = os.getenv("SANDBOX_ENGINE", "docker").lower()
SANDBOX_DOCKER_IMAGE = os.getenv("SANDBOX_DOCKER_IMAGE", "gitplayground-sandbox:latest")
SANDBOX_DOCKER_CPUS = os.getenv("SANDBOX_DOCKER_CPUS", "1.0")
SANDBOX_DOCKER_MEMORY = os.getenv("SANDBOX_DOCKER_MEMORY", "512m")
SANDBOX_DOCKER_PIDS_LIMIT = os.getenv("SANDBOX_DOCKER_PIDS_LIMIT", "256")
RUNNING_TESTS = "test" in sys.argv
SANDBOX_ALLOW_LOCAL_FALLBACK = (
    os.getenv(
        "SANDBOX_ALLOW_LOCAL_FALLBACK",
        "true" if (settings.DEBUG or RUNNING_TESTS) else "false",
    ).lower()
    == "true"
)
audit_logger = logging.getLogger("apps.core.sandbox.audit")

# Deterministic git environment — see sandbox_git.py


def validated_sandbox_workspace(repo_path: str) -> Path:
    """Resolve path and ensure it stays inside SANDBOX_ROOT (delete/reset guard)."""
    ensure_sandbox_root()
    root = SANDBOX_ROOT.resolve()
    path = Path(repo_path).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"repo_path outside sandbox root: {path}")
    return path


def rmtree_sandbox_workspace_if_safe(repo_path: str) -> bool:
    """Delete workspace only if under SANDBOX_ROOT. Returns True if deleted or absent."""
    try:
        workspace = validated_sandbox_workspace(repo_path)
    except ValueError:
        audit_logger.error(
            "blocked destructive sandbox op",
            extra={"event": "sandbox_path_guard", "repo_path": repo_path},
        )
        return False
    if workspace.exists():
        shutil.rmtree(workspace, ignore_errors=True)
    return True


# Text file limits in the sandbox repo (cat read / UI file editor).
SANDBOX_TEXT_FILE_READ_MAX_BYTES = 256 * 1024
SANDBOX_TEXT_FILE_WRITE_MAX_BYTES = 256 * 1024

# Pseudo-prompt in the user log (do not expose host filesystem paths).
TERMINAL_PROMPT_PREFIX = "user@gitplayground:~/repo$ "


@dataclass
class CommandResult:
    command: str
    return_code: int
    output: str
    duration_ms: int


def _task_workspace_name(user: User, task: Task) -> str:
    return f"user{user.id}_task{task.id}_{uuid4().hex[:8]}"


def _is_docker_session(session: SandboxSession) -> bool:
    return session.container_id.startswith("docker-")


def is_docker_session(session: SandboxSession) -> bool:
    return _is_docker_session(session)


def _docker_available() -> bool:
    try:
        result = subprocess.run(
            ["docker", "version", "--format", "{{.Server.Version}}"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        return result.returncode == 0
    except Exception:  # noqa: BLE001
        return False


def _start_docker_container(container_id: str, workspace: Path) -> bool:
    if not _docker_available():
        return False
    command = [
        "docker",
        "run",
        "-d",
        "--name",
        container_id,
        "--network",
        "none",
        "--cpus",
        SANDBOX_DOCKER_CPUS,
        "--memory",
        SANDBOX_DOCKER_MEMORY,
        "--pids-limit",
        SANDBOX_DOCKER_PIDS_LIMIT,
        "-v",
        f"{workspace.resolve()}:/workspace",
        "-w",
        "/workspace",
        SANDBOX_DOCKER_IMAGE,
        "sh",
        "-c",
        "while true; do sleep 3600; done",
    ]
    # nosemgrep: python.lang.security.audit.dangerous-subprocess-use-tainted-env-args.dangerous-subprocess-use-tainted-env-args
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    return result.returncode == 0


def _session_log_path(session: SandboxSession) -> Path:
    ensure_sandbox_root()
    logs_dir = SANDBOX_ROOT / "_logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    session_key = session.id or session.container_id or "unknown"
    return logs_dir / f"session_{session_key}.terminal.log"


def _legacy_repo_log_path(session: SandboxSession) -> Path:
    return Path(session.repo_path) / ".gp_terminal.log"


def _cleanup_legacy_repo_log(session: SandboxSession) -> None:
    legacy = _legacy_repo_log_path(session)
    if legacy.exists():
        legacy.unlink(missing_ok=True)


def _sanitize_terminal_output(repo_root: str, command: str, text: str) -> str:
    """Strip sandbox absolute paths and simplify noisy git output for the learner terminal."""
    if not text:
        return text
    out = text
    roots: set[str] = set()
    try:
        roots.add(str(Path(repo_root).resolve()))
    except OSError:
        pass
    roots.add(str(Path(repo_root)))
    for root in roots:
        if len(root) < 3:
            continue
        out = out.replace(root, "~/repo")
        out = out.replace(root.replace("\\", "/"), "~/repo")
        out = out.replace(root.replace("/", "\\"), "~/repo")

    cmd_l = (command or "").strip().lower()
    out_l = out.lower()
    if cmd_l == "git init" or cmd_l.startswith("git init "):
        if "reinitialized existing git repository" in out_l:
            return "Репозиторий Git в этой песочнице уже инициализирован."
        if "initialized empty git repository" in out_l:
            return "Пустой репозиторий Git создан в ~/repo/."
    if command:
        return out.strip()
    return out


def _write_log(
    session: SandboxSession,
    command: str,
    output: str,
    *,
    include_in_user_log: bool = True,
) -> None:
    if not include_in_user_log:
        return
    path = _session_log_path(session)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(f"{TERMINAL_PROMPT_PREFIX}{command}\n{output}\n")


def write_session_log(
    session: SandboxSession,
    command: str,
    output: str,
    *,
    include_in_user_log: bool = True,
) -> None:
    _write_log(session, command, output, include_in_user_log=include_in_user_log)


def _audit_log(
    session: SandboxSession,
    command: str,
    *,
    allowed: bool,
    reason: str,
    actor: str = "user",
    metadata: dict | None = None,
) -> None:
    task_external_id = None
    if session.task_id:
        try:
            task_external_id = session.task.external_id
        except Task.DoesNotExist:
            task_external_id = None
    payload = {
        "event": "sandbox_command_policy",
        "actor": actor,
        "session_id": session.id,
        "user_id": session.user_id,
        "task_id": session.task_id,
        "task_external_id": task_external_id,
        "engine": "docker" if _is_docker_session(session) else "local",
        "allowed": allowed,
        "reason": reason,
        "command": command,
        "timestamp": timezone.now().isoformat(),
    }
    if metadata:
        payload.update(metadata)
    audit_logger.info(json.dumps(payload, ensure_ascii=False))


def audit_playground_repo_file(
    session: SandboxSession, op: str, rel_path: str, *, allowed: bool, extra: dict | None = None
) -> None:
    """Audit sandbox file read/write operations (no shell)."""
    meta: dict = {"path": rel_path}
    if extra:
        meta.update(extra)
    _audit_log(session, f"file:{op}", allowed=allowed, reason=f"repo_file_{op}", metadata=meta)


def _read_log_tail(session: SandboxSession, max_chars: int = 8000) -> str:
    path = _session_log_path(session)
    if not path.exists():
        return "Песочница готова. Можно вводить команды Git.\n"
    content = path.read_text(encoding="utf-8")
    tail = content[-max_chars:]
    sanitized = _sanitize_terminal_output(session.repo_path, "", tail)
    normalized = sanitized.replace(f"{TERMINAL_PROMPT_PREFIX}{TERMINAL_PROMPT_PREFIX}", TERMINAL_PROMPT_PREFIX)
    normalized = normalized.replace(f"{TERMINAL_PROMPT_PREFIX} {TERMINAL_PROMPT_PREFIX}", TERMINAL_PROMPT_PREFIX)
    normalized = normalized.replace(f"{TERMINAL_PROMPT_PREFIX}", f"\n{TERMINAL_PROMPT_PREFIX}")
    normalized = normalized.lstrip("\n")
    return normalized.rstrip()


def _repo_size_bytes(path: Path) -> int:
    total = 0
    for item in path.rglob("*"):
        if item.is_file():
            try:
                total += item.stat().st_size
            except OSError:
                continue
    return total


def _repo_quota_violation(session: SandboxSession) -> str | None:
    quota_bytes = int(session.max_repo_size_mb) * 1024 * 1024
    current_bytes = _repo_size_bytes(Path(session.repo_path))
    if current_bytes > quota_bytes:
        return (
            f"Repository quota exceeded: {current_bytes // (1024 * 1024)}MB > "
            f"{session.max_repo_size_mb}MB."
        )
    return None


def read_text_file_from_repo(session: SandboxSession, relative_path: str) -> tuple[bool, str, bool]:
    """Read one text file inside the repo. (ok, text or error message, truncated)."""
    status, raw, truncated = read_repo_file_bytes(
        session.repo_path, relative_path, SANDBOX_TEXT_FILE_READ_MAX_BYTES
    )
    if status == "blocked":
        return False, "Path escapes sandbox and is blocked.", False
    if status == "missing":
        return False, "File does not exist.", False
    if status == "not_file":
        return False, "Not a regular file.", False
    if status == "io_error":
        return False, FILE_READ_FAILED, False
    text = raw.decode("utf-8", errors="replace")
    return True, text, truncated


def write_text_file_to_repo(session: SandboxSession, relative_path: str, content: str) -> tuple[bool, str]:
    """Write UTF-8 text to a file inside the repo (no shell)."""
    if "\x00" in content:
        return False, "Null bytes in content are not allowed."
    encoded = content.encode("utf-8")
    if len(encoded) > SANDBOX_TEXT_FILE_WRITE_MAX_BYTES:
        return False, f"Content exceeds limit ({SANDBOX_TEXT_FILE_WRITE_MAX_BYTES} bytes)."
    status, backup = write_repo_file_bytes(session.repo_path, relative_path, encoded)
    if status == "blocked":
        return False, "Path escapes sandbox and is blocked."
    if status == "io_error":
        return False, FILE_WRITE_FAILED
    violation = _repo_quota_violation(session)
    if violation:
        restore_or_remove_repo_file(session.repo_path, relative_path, backup)
        return False, f"{violation} Write was reverted."
    return True, ""


def get_active_session(user: User, task: Task) -> SandboxSession | None:
    now = timezone.now()
    return (
        SandboxSession.objects.filter(
            user=user,
            task=task,
            status__in=[SandboxSession.Status.STARTING, SandboxSession.Status.ACTIVE],
            expires_at__gt=now,
        )
        .order_by("-last_activity_at")
        .first()
    )


def get_or_create_active_session(user: User, task: Task) -> SandboxSession:
    session = get_active_session(user, task)
    if session:
        _cleanup_legacy_repo_log(session)
        return session

    ensure_sandbox_root()
    workspace = SANDBOX_ROOT / _task_workspace_name(user, task)
    seed_workspace_from_assets(task, workspace)
    container_id = f"local-{uuid4().hex}"
    if SANDBOX_ENGINE != "docker" and not SANDBOX_ALLOW_LOCAL_FALLBACK:
        raise RuntimeError("Local sandbox engine is disabled in production. Use SANDBOX_ENGINE=docker.")
    if SANDBOX_ENGINE == "docker":
        proposed = f"docker-{uuid4().hex[:12]}"
        if _start_docker_container(proposed, workspace):
            container_id = proposed
        elif not SANDBOX_ALLOW_LOCAL_FALLBACK:
            raise RuntimeError("Docker sandbox runtime is required but unavailable.")
    now = timezone.now()
    session = SandboxSession.objects.create(
        user=user,
        task=task,
        container_id=container_id,
        repo_path=str(workspace),
        status=SandboxSession.Status.ACTIVE,
        timeout_seconds=30,
        max_repo_size_mb=10,
        expires_at=now + timedelta(hours=2),
    )
    _write_log(
        session,
        "session:start",
        f"Sandbox ready in {workspace} (engine={'docker' if _is_docker_session(session) else 'local'})",
        include_in_user_log=False,
    )
    _cleanup_legacy_repo_log(session)
    return session


def _repo_io_status_proc(verb: str, status: str, payload: str, path: str) -> subprocess.CompletedProcess:
    if status == "ok":
        return subprocess.CompletedProcess(["policy"], 0, payload, "")
    if status == "blocked":
        return subprocess.CompletedProcess(
            ["policy"], 1, "", "Path escapes sandbox and is blocked."
        )
    if status == "git_protected":
        return subprocess.CompletedProcess(
            ["policy"], 1, "", f"{verb}: нельзя изменять каталог `.git`."
        )
    if status == "missing":
        return subprocess.CompletedProcess(
            ["policy"], 1, "", f"{verb}: нет такого файла или каталога: {path}"
        )
    if status == "not_file":
        return subprocess.CompletedProcess(["policy"], 1, "", f"{verb}: не файл: {path}")
    if status == "not_dir":
        return subprocess.CompletedProcess(["policy"], 1, "", f"find: не каталог: {path}")
    if status == "is_dir":
        return subprocess.CompletedProcess(
            ["policy"], 1, "", f"rm: это каталог, а не файл: {path}"
        )
    return subprocess.CompletedProcess(["policy"], 1, "", f"{verb}: операция не удалась.")


def run_command(
    session: SandboxSession,
    command: str,
    *,
    include_in_user_log: bool = True,
) -> CommandResult:
    started = time.perf_counter()
    _cleanup_legacy_repo_log(session)
    if not command.strip():
        return CommandResult(command=command, return_code=1, output="Empty command", duration_ms=0)

    allowed, policy_kind, policy_data = parse_user_command(command)
    _audit_log(session, command, allowed=allowed, reason=policy_kind, metadata=policy_data)
    if not allowed:
        return CommandResult(
            command=command,
            return_code=126,
            output=(
                "Команда запрещена политикой песочницы. Разрешено: "
                f"{SANDBOX_ALLOWED_COMMANDS_SUMMARY}. "
                "Многострочный текст — команда `nano путь` в терминале."
            ),
            duration_ms=0,
        )

    if policy_kind == "git":
        args = policy_data["args"]
        if _is_docker_session(session):
            proc = subprocess.run(
                ["docker", "exec", session.container_id, *args],
                capture_output=True,
                text=True,
                timeout=session.timeout_seconds,
                check=False,
            )
        else:
            proc = subprocess.run(
                args,
                cwd=session.repo_path,
                capture_output=True,
                text=True,
                timeout=session.timeout_seconds,
                check=False,
                env=git_env(),
            )
    elif policy_kind in {"touch", "type_nul_redirect"}:
        if policy_kind == "touch":
            ok = touch_repo_file(session.repo_path, policy_data["path"])
        else:
            ok = write_empty_repo_file(session.repo_path, policy_data["path"])
        if not ok:
            return CommandResult(
                command=command,
                return_code=1,
                output="Path escapes sandbox and is blocked.",
                duration_ms=0,
            )
        proc = subprocess.CompletedProcess(["policy"], 0, "", "")
    elif policy_kind == "echo_redirect":
        ok = append_repo_text_line(
            session.repo_path,
            policy_data["path"],
            policy_data["text"],
            append=policy_data["mode"] == ">>",
        )
        if not ok:
            return CommandResult(
                command=command,
                return_code=1,
                output="Path escapes sandbox and is blocked.",
                duration_ms=0,
            )
        proc = subprocess.CompletedProcess(["policy"], 0, "", "")
    elif policy_kind == "pwd":
        proc = subprocess.CompletedProcess(["policy"], 0, "~/repo", "")
    elif policy_kind == "ls":
        status, payload = list_repo_path(session.repo_path, policy_data["path"])
        if status == "blocked":
            return CommandResult(
                command=command,
                return_code=1,
                output="Path escapes sandbox and is blocked.",
                duration_ms=0,
            )
        if status == "missing":
            proc = subprocess.CompletedProcess(
                ["policy"], 1, "", f"ls: нет такого файла или каталога: {policy_data['path']}"
            )
        else:
            proc = subprocess.CompletedProcess(["policy"], 0, payload, "")
    elif policy_kind == "mkdir":
        status, detail = mkdir_repo_path(
            session.repo_path, policy_data["path"], parents=policy_data["parents"]
        )
        if status == "blocked":
            return CommandResult(
                command=command,
                return_code=1,
                output="Path escapes sandbox and is blocked.",
                duration_ms=0,
            )
        if status == "exists":
            proc = subprocess.CompletedProcess(
                ["policy"],
                1,
                "",
                f"mkdir: каталог уже существует: {detail}",
            )
        elif status == "io_error":
            proc = subprocess.CompletedProcess(["policy"], 1, "", MKDIR_FAILED)
        else:
            proc = subprocess.CompletedProcess(["policy"], 0, "", "")
    elif policy_kind == "cat_read":
        ok, payload, truncated = read_text_file_from_repo(session, policy_data["path"])
        if not ok:
            proc = subprocess.CompletedProcess(["policy"], 1, "", payload)
        else:
            suffix = "\n[Output truncated to sandbox read limit.]" if truncated else ""
            proc = subprocess.CompletedProcess(["policy"], 0, f"{payload}{suffix}", "")
    elif policy_kind == "nano_open":
        path = policy_data["path"]
        proc = subprocess.CompletedProcess(
            ["policy"],
            0,
            f"Редактор: {path} (Ctrl+S — сохранить, Ctrl+X — выйти)",
            "",
        )
    elif policy_kind == "echo_print":
        proc = subprocess.CompletedProcess(["policy"], 0, policy_data["text"], "")
    elif policy_kind == "head_read":
        status, payload = head_repo_file(
            session.repo_path, policy_data["path"], lines=policy_data["lines"]
        )
        proc = _repo_io_status_proc("head", status, payload, policy_data["path"])
    elif policy_kind == "tail_read":
        status, payload = tail_repo_file(
            session.repo_path, policy_data["path"], lines=policy_data["lines"]
        )
        proc = _repo_io_status_proc("tail", status, payload, policy_data["path"])
    elif policy_kind == "wc_read":
        status, payload = wc_repo_file(
            session.repo_path, policy_data["path"], lines_only=policy_data["lines_only"]
        )
        proc = _repo_io_status_proc("wc", status, payload, policy_data["path"])
    elif policy_kind == "cp_file":
        status, detail = cp_repo_file(
            session.repo_path, policy_data["src"], policy_data["dst"]
        )
        proc = _repo_io_status_proc("cp", status, detail, policy_data["src"])
    elif policy_kind == "mv_file":
        status, detail = mv_repo_file(
            session.repo_path, policy_data["src"], policy_data["dst"]
        )
        proc = _repo_io_status_proc("mv", status, detail, policy_data["src"])
    elif policy_kind == "rm_file":
        status, detail = rm_repo_path(session.repo_path, policy_data["path"])
        proc = _repo_io_status_proc("rm", status, detail, policy_data["path"])
    elif policy_kind == "find_paths":
        status, payload = find_repo_paths(session.repo_path, policy_data["path"])
        proc = _repo_io_status_proc("find", status, payload, policy_data["path"])
    elif policy_kind == "whoami":
        proc = subprocess.CompletedProcess(["policy"], 0, "gitplayground", "")
    elif policy_kind == "clear":
        proc = subprocess.CompletedProcess(["policy"], 0, "", "")
    else:
        return CommandResult(command=command, return_code=1, output="Unsupported policy command.", duration_ms=0)
    duration_ms = int((time.perf_counter() - started) * 1000)
    output = (proc.stdout or "") + (proc.stderr or "")
    return_code = proc.returncode
    quota_error = _repo_quota_violation(session)
    if quota_error:
        return_code = 122
        output = f"{output}\n{quota_error}".strip()
    output = _sanitize_terminal_output(session.repo_path, command, output.strip())
    _write_log(session, command, output or "(no output)", include_in_user_log=include_in_user_log)
    SandboxSession.objects.filter(pk=session.pk).update(
        last_activity_at=timezone.now(),
        status=SandboxSession.Status.ACTIVE,
    )
    return CommandResult(
        command=command,
        return_code=return_code,
        output=output.strip(),
        duration_ms=duration_ms,
    )


def reset_session(session: SandboxSession) -> SandboxSession:
    rmtree_sandbox_workspace_if_safe(session.repo_path)
    task = session.task
    user = session.user
    session.status = SandboxSession.Status.STOPPED
    session.save(update_fields=["status", "last_activity_at"])
    if not task:
        return session
    return get_or_create_active_session(user=user, task=task)


def stop_session(session: SandboxSession) -> None:
    if _is_docker_session(session):
        subprocess.run(
            ["docker", "rm", "-f", session.container_id],
            capture_output=True,
            text=True,
            check=False,
        )
    rmtree_sandbox_workspace_if_safe(session.repo_path)
    session.status = SandboxSession.Status.STOPPED
    session.save(update_fields=["status", "last_activity_at"])

