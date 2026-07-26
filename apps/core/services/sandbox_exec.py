"""Run argv inside a sandbox session (Docker exec or local subprocess)."""

from __future__ import annotations

import subprocess

from apps.sandbox.models import SandboxSession


def run_sandbox_argv(
    session: SandboxSession,
    args: list[str],
    *,
    env: dict[str, str] | None = None,
    timeout: int | None = None,
) -> subprocess.CompletedProcess:
    """Execute ``args`` in the session workspace; Docker sessions use ``docker exec``."""
    timeout_sec = session.timeout_seconds if timeout is None else timeout
    if session.container_id.startswith("docker-"):
        return subprocess.run(
            ["docker", "exec", session.container_id, *args],
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            check=False,
        )
    return subprocess.run(
        args,
        cwd=session.repo_path,
        capture_output=True,
        text=True,
        timeout=timeout_sec,
        check=False,
        env=env,
    )
