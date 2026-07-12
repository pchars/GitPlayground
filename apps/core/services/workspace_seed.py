"""Initial sandbox workspace seeding."""

from __future__ import annotations

import base64
import subprocess
import zipfile
from pathlib import Path

from apps.tasks.models import Task, TaskAsset

from .sandbox_git import SANDBOX_GIT_USER_EMAIL, SANDBOX_GIT_USER_NAME, git_env


def safe_extract_zip(archive: zipfile.ZipFile, dest: Path) -> None:
    """Extract zip only inside dest (zip-slip protection)."""
    dest_resolved = dest.resolve()
    for member in archive.namelist():
        if member.endswith("/"):
            continue
        target = (dest / member).resolve()
        if target != dest_resolved and dest_resolved not in target.parents:
            raise ValueError(f"Zip entry escapes workspace: {member}")
    archive.extractall(dest)


def seed_workspace_from_assets(task: Task, workspace: Path) -> None:
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
                safe_extract_zip(archive, workspace)
            zip_path.unlink(missing_ok=True)
        elif payload.startswith("base64:"):
            raw = base64.b64decode(payload.removeprefix("base64:"))
            (workspace / "start_repo.bin").write_bytes(raw)
        else:
            (workspace / "README_TASK.txt").write_text(payload, encoding="utf-8")
    start_meta = (task.metadata or {}).get("start") if isinstance(task.metadata, dict) else {}
    requires = start_meta.get("requires", []) if isinstance(start_meta, dict) else []
    env = git_env()

    def _git(*args: str) -> None:
        subprocess.run(
            ["git", *args], cwd=workspace, check=False, capture_output=True, text=True, env=env
        )

    needs_repo = bool(start_repo_asset) or bool(
        set(requires) & {"repo_initialized", "hello_committed", "feature_branch_exists"}
    )
    if task.slug == "init_repo":
        needs_repo = False
    if needs_repo:
        _git("init")
        _git("config", "user.email", SANDBOX_GIT_USER_EMAIL)
        _git("config", "user.name", SANDBOX_GIT_USER_NAME)
    if "hello_committed" in requires:
        hello_path = workspace / "hello.txt"
        if not hello_path.exists():
            hello_path.write_text("Hello, Git!\n", encoding="utf-8")
        _git("add", "hello.txt")
        _git("commit", "-m", "Add hello")
    if "feature_branch_exists" in requires:
        if task.slug == "switch_branch":
            _git("checkout", "-b", "feature-x")
            (workspace / "feature.txt").write_text("Feature work in progress\n", encoding="utf-8")
            _git("add", "feature.txt")
            _git("commit", "-m", "Add feature")
        else:
            _git("checkout", "-b", "feature-x")
            _git("checkout", "main")

    if task.slug == "ignore_node_modules":
        node_modules = workspace / "node_modules"
        node_modules.mkdir(parents=True, exist_ok=True)
        (node_modules / "dummy.js").write_text("// dependency stub\n", encoding="utf-8")

    if task.slug == "untrack_cached":
        secrets = workspace / "secrets.env"
        secrets.write_text("SECRET=1\n", encoding="utf-8")
        _git("add", "secrets.env")
        _git("commit", "-m", "Track secrets by mistake")

    if task.slug == "ignore_exceptions":
        (workspace / "debug.log").write_text("debug output\n", encoding="utf-8")
        (workspace / "important.log").write_text("important output\n", encoding="utf-8")

    if task.slug == "setup_ignore":
        (workspace / "app.log").write_text("log line\n", encoding="utf-8")
        (workspace / ".env").write_text("KEY=value\n", encoding="utf-8")
        cache_dir = workspace / "__pycache__"
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / "module.pyc").write_bytes(b"\x00")
