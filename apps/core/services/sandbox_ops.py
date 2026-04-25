from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import timedelta
import json
import logging
from pathlib import Path
import os
import shlex
import shutil
import subprocess
import sys
import time
import zipfile
from uuid import uuid4

from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone

from apps.sandbox.models import SandboxSession
from apps.tasks.models import Task, TaskAsset


SANDBOX_ROOT = Path(settings.BASE_DIR) / ".sandboxes"
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


def validated_sandbox_workspace(repo_path: str) -> Path:
    """Разрешить путь и убедиться, что он внутри SANDBOX_ROOT (защита для delete/reset)."""
    _ensure_sandbox_root()
    root = SANDBOX_ROOT.resolve()
    path = Path(repo_path).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"repo_path outside sandbox root: {path}")
    return path


def rmtree_sandbox_workspace_if_safe(repo_path: str) -> bool:
    """Удалить рабочую директорию только если она лежит под SANDBOX_ROOT. Возвращает True, если удаление выполнено или каталога не было."""
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


# Лимиты текстовых файлов в репозитории песочницы (чтение cat / редактор в UI).
SANDBOX_TEXT_FILE_READ_MAX_BYTES = 256 * 1024
SANDBOX_TEXT_FILE_WRITE_MAX_BYTES = 256 * 1024

# Псевдо-промпт в пользовательском логе (не раскрывать реальные пути хоста).
TERMINAL_PROMPT_PREFIX = "user@gitplayground:~/repo$ "


@dataclass
class CommandResult:
    command: str
    return_code: int
    output: str
    duration_ms: int


def _ensure_sandbox_root() -> None:
    SANDBOX_ROOT.mkdir(exist_ok=True)


def _task_workspace_name(user: User, task: Task) -> str:
    return f"user{user.id}_task{task.id}_{uuid4().hex[:8]}"


def _is_docker_session(session: SandboxSession) -> bool:
    return session.container_id.startswith("docker-")


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
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    return result.returncode == 0


def _session_log_path(session: SandboxSession) -> Path:
    _ensure_sandbox_root()
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
    """Убрать абсолютные пути к песочнице и упростить шумный вывод git для учебного терминала."""
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
    """Аудит операций чтения/записи файлов в песочнице (обход shell)."""
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


def _seed_workspace_from_assets(task: Task, workspace: Path) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    start_repo_asset = (
        TaskAsset.objects.filter(task=task, asset_type=TaskAsset.AssetType.START_REPO)
        .order_by("sort_order")
        .first()
    )
    if start_repo_asset and start_repo_asset.content.strip():
        payload = start_repo_asset.content.strip()
        if payload.startswith("base64zip:"):
            zipped = base64.b64decode(payload.removeprefix("base64zip:"))
            zip_path = workspace / "__start_repo__.zip"
            zip_path.write_bytes(zipped)
            with zipfile.ZipFile(zip_path, "r") as archive:
                archive.extractall(workspace)
            zip_path.unlink(missing_ok=True)
        elif payload.startswith("base64:"):
            raw = base64.b64decode(payload.removeprefix("base64:"))
            (workspace / "start_repo.bin").write_bytes(raw)
        else:
            (workspace / "README_TASK.txt").write_text(payload, encoding="utf-8")
    start_meta = (task.metadata or {}).get("start") if isinstance(task.metadata, dict) else {}
    requires = start_meta.get("requires", []) if isinstance(start_meta, dict) else []
    # Для init_repo репозиторий должен быть "чистым", иначе git init сразу вернет reinitialized.
    # Для остальных задач, где есть предпосылки по истории/веткам, поднимаем git-репозиторий заранее.
    needs_repo = bool(start_repo_asset) or bool(
        set(requires) & {"repo_initialized", "hello_committed", "feature_branch_exists"}
    )
    if task.slug == "init_repo":
        needs_repo = False
    if needs_repo:
        subprocess.run(["git", "init"], cwd=workspace, check=False, capture_output=True, text=True)
        subprocess.run(
            ["git", "config", "user.email", "gitplayground@example.local"],
            cwd=workspace,
            check=False,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "GitPlayground Bot"],
            cwd=workspace,
            check=False,
            capture_output=True,
            text=True,
        )
    if "hello_committed" in requires:
        hello_path = workspace / "hello.txt"
        if not hello_path.exists():
            hello_path.write_text("Hello, Git!\n", encoding="utf-8")
        subprocess.run(["git", "add", "hello.txt"], cwd=workspace, check=False, capture_output=True, text=True)
        subprocess.run(
            ["git", "commit", "-m", "Add hello"],
            cwd=workspace,
            check=False,
            capture_output=True,
            text=True,
        )
    if "feature_branch_exists" in requires:
        subprocess.run(
            ["git", "checkout", "-b", "feature-x"],
            cwd=workspace,
            check=False,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["git", "checkout", "main"],
            cwd=workspace,
            check=False,
            capture_output=True,
            text=True,
        )


def _resolve_repo_relative_path(session: SandboxSession, candidate: str) -> Path | None:
    repo_root = Path(session.repo_path).resolve()
    path = (repo_root / candidate).resolve()
    if path == repo_root or repo_root in path.parents:
        return path
    return None


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


def _relative_path_has_dotdot(relative_path: str) -> bool:
    norm = relative_path.strip().replace("\\", "/")
    if not norm or norm.startswith("/"):
        return True
    return ".." in Path(norm).parts


def read_text_file_from_repo(session: SandboxSession, relative_path: str) -> tuple[bool, str, bool]:
    """Читает один текстовый файл внутри репозитория. (ok, текст или сообщение об ошибке, truncated)."""
    normalized = relative_path.strip().replace("\\", "/")
    if _relative_path_has_dotdot(normalized):
        return False, "Path must not contain '..'.", False
    file_path = _resolve_repo_relative_path(session, normalized)
    if not file_path:
        return False, "Path escapes sandbox and is blocked.", False
    if not file_path.exists():
        return False, "File does not exist.", False
    if not file_path.is_file():
        return False, "Not a regular file.", False
    try:
        raw = file_path.read_bytes()
    except OSError as exc:
        return False, f"Cannot read file: {exc}", False
    truncated = len(raw) > SANDBOX_TEXT_FILE_READ_MAX_BYTES
    raw = raw[:SANDBOX_TEXT_FILE_READ_MAX_BYTES]
    text = raw.decode("utf-8", errors="replace")
    return True, text, truncated


def write_text_file_to_repo(session: SandboxSession, relative_path: str, content: str) -> tuple[bool, str]:
    """Записывает UTF-8 текст в файл внутри репозитория (без shell)."""
    normalized = relative_path.strip().replace("\\", "/")
    if _relative_path_has_dotdot(normalized):
        return False, "Path must not contain '..'."
    if "\x00" in content:
        return False, "Null bytes in content are not allowed."
    encoded = content.encode("utf-8")
    if len(encoded) > SANDBOX_TEXT_FILE_WRITE_MAX_BYTES:
        return False, f"Content exceeds limit ({SANDBOX_TEXT_FILE_WRITE_MAX_BYTES} bytes)."
    file_path = _resolve_repo_relative_path(session, normalized)
    if not file_path:
        return False, "Path escapes sandbox and is blocked."
    backup: bytes | None = None
    if file_path.exists() and file_path.is_file():
        try:
            backup = file_path.read_bytes()[: SANDBOX_TEXT_FILE_WRITE_MAX_BYTES + 1]
        except OSError as exc:
            return False, f"Cannot read existing file: {exc}"
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(encoded)
    except OSError as exc:
        return False, f"Cannot write file: {exc}"
    violation = _repo_quota_violation(session)
    if violation:
        try:
            if backup is not None:
                file_path.write_bytes(backup)
            else:
                file_path.unlink(missing_ok=True)
        except OSError:
            pass
        return False, f"{violation} Write was reverted."
    return True, ""


def _parse_user_command(command: str) -> tuple[bool, str, dict]:
    try:
        tokens = shlex.split(command)
    except ValueError:
        return False, "syntax_error", {}
    if not tokens:
        return False, "empty_command", {}

    root = tokens[0]
    if root == "git":
        return True, "git", {"args": tokens}

    if root == "touch" and len(tokens) == 2:
        return True, "touch", {"path": tokens[1]}

    # Только «cat <path>» без флагов: чтение через Python, без запуска /bin/cat (инъекции через имена/флаги).
    if root == "cat" and len(tokens) == 2:
        target = tokens[1]
        if target.startswith("-"):
            return False, "cat_flags_not_allowed", {}
        if _relative_path_has_dotdot(target):
            return False, "cat_path_dotdot", {}
        return True, "cat_read", {"path": target}

    if root == "type" and len(tokens) == 4 and tokens[1].lower() == "nul" and tokens[2] == ">":
        return True, "type_nul_redirect", {"path": tokens[3]}

    if root == "echo":
        op_index = -1
        op_token = ""
        for idx, token in enumerate(tokens):
            if token in {">", ">>"}:
                op_index = idx
                op_token = token
                break
        if op_index <= 1:
            return False, "echo_missing_body_or_redirect", {}
        if op_index + 1 >= len(tokens) or op_index + 2 != len(tokens):
            return False, "echo_invalid_redirect_target", {}
        text = " ".join(tokens[1:op_index]).strip()
        if not text:
            return False, "echo_empty_text", {}
        return True, "echo_redirect", {"text": text, "mode": op_token, "path": tokens[op_index + 1]}

    return False, "command_not_allowed", {"command_root": root}


def get_or_create_active_session(user: User, task: Task) -> SandboxSession:
    now = timezone.now()
    session = (
        SandboxSession.objects.filter(
            user=user,
            task=task,
            status__in=[SandboxSession.Status.STARTING, SandboxSession.Status.ACTIVE],
            expires_at__gt=now,
        )
        .order_by("-last_activity_at")
        .first()
    )
    if session:
        _cleanup_legacy_repo_log(session)
        return session

    _ensure_sandbox_root()
    workspace = SANDBOX_ROOT / _task_workspace_name(user, task)
    _seed_workspace_from_assets(task, workspace)
    container_id = f"local-{uuid4().hex}"
    if SANDBOX_ENGINE != "docker" and not SANDBOX_ALLOW_LOCAL_FALLBACK:
        raise RuntimeError("Local sandbox engine is disabled in production. Use SANDBOX_ENGINE=docker.")
    if SANDBOX_ENGINE == "docker":
        proposed = f"docker-{uuid4().hex[:12]}"
        if _start_docker_container(proposed, workspace):
            container_id = proposed
        elif not SANDBOX_ALLOW_LOCAL_FALLBACK:
            raise RuntimeError("Docker sandbox runtime is required but unavailable.")
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


def run_command(
    session: SandboxSession,
    command: str,
    allow_non_git: bool = False,
    *,
    include_in_user_log: bool = True,
) -> CommandResult:
    started = time.perf_counter()
    _cleanup_legacy_repo_log(session)
    if not command.strip():
        return CommandResult(command=command, return_code=1, output="Empty command", duration_ms=0)

    policy_kind = "internal"
    policy_data: dict = {}
    if not allow_non_git:
        allowed, policy_kind, policy_data = _parse_user_command(command)
        _audit_log(session, command, allowed=allowed, reason=policy_kind, metadata=policy_data)
        if not allowed:
            return CommandResult(
                command=command,
                return_code=126,
                output=(
                    "Команда запрещена политикой песочницы. Разрешено: git, "
                    "touch <файл>, cat <файл>, type nul > <файл>, "
                    "echo <текст> > <файл>, echo <текст> >> <файл>. "
                    "Многострочный текст — через блок «Редактор файла» на странице (без shell)."
                ),
                duration_ms=0,
            )

    if allow_non_git:
        if _is_docker_session(session):
            proc = subprocess.run(
                ["docker", "exec", session.container_id, "sh", "-lc", command],
                capture_output=True,
                text=True,
                timeout=session.timeout_seconds,
                check=False,
            )
        else:
            args = shlex.split(command)
            if not args:
                return CommandResult(command=command, return_code=1, output="Invalid command", duration_ms=0)
            proc = subprocess.run(
                args,
                cwd=session.repo_path,
                capture_output=True,
                text=True,
                timeout=session.timeout_seconds,
                check=False,
            )
    elif policy_kind == "git":
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
            )
    elif policy_kind in {"touch", "type_nul_redirect"}:
        file_path = _resolve_repo_relative_path(session, policy_data["path"])
        if not file_path:
            return CommandResult(
                command=command,
                return_code=1,
                output="Path escapes sandbox and is blocked.",
                duration_ms=0,
            )
        file_path.parent.mkdir(parents=True, exist_ok=True)
        if policy_kind == "touch":
            file_path.touch(exist_ok=True)
        else:
            file_path.write_text("", encoding="utf-8")
        proc = subprocess.CompletedProcess(["policy"], 0, "", "")
    elif policy_kind == "echo_redirect":
        file_path = _resolve_repo_relative_path(session, policy_data["path"])
        if not file_path:
            return CommandResult(
                command=command,
                return_code=1,
                output="Path escapes sandbox and is blocked.",
                duration_ms=0,
            )
        file_path.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if policy_data["mode"] == ">>" else "w"
        with file_path.open(mode, encoding="utf-8") as handle:
            handle.write(policy_data["text"])
            handle.write("\n")
        proc = subprocess.CompletedProcess(["policy"], 0, "", "")
    elif policy_kind == "cat_read":
        ok, payload, truncated = read_text_file_from_repo(session, policy_data["path"])
        if not ok:
            proc = subprocess.CompletedProcess(["policy"], 1, "", payload)
        else:
            suffix = "\n[Output truncated to sandbox read limit.]" if truncated else ""
            proc = subprocess.CompletedProcess(["policy"], 0, f"{payload}{suffix}", "")
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


def session_log(session: SandboxSession) -> str:
    return _read_log_tail(session)

