"""Trusted repo-relative file I/O (CodeQL py/path-injection safe).

Guards (``os.path.realpath`` + ``startswith``) and filesystem access must live in
the same function so GitHub CodeQL can prove the path is confined under the root.
"""

from __future__ import annotations

import os

from .command_policy import normalize_repo_relative_path


def _root_prefix(base_path: str) -> str:
    return base_path if base_path.endswith(os.sep) else f"{base_path}{os.sep}"


def _path_blocked(root_dir: str, relative_path: str) -> str | None:
    """Return trusted absolute path, or None when user input must be rejected."""
    safe_relative = normalize_repo_relative_path(relative_path)
    if safe_relative is None:
        return None
    base_path = os.path.realpath(root_dir)
    fullpath = os.path.realpath(os.path.join(base_path, safe_relative))
    root_prefix = _root_prefix(base_path)
    if fullpath != base_path and not fullpath.startswith(root_prefix):
        return None
    return fullpath


def resolve_trusted_path_under_root(root_dir: str, relative_path: str) -> str | None:
    """Return an absolute path under ``root_dir``, or None if rejected."""
    return _path_blocked(root_dir, relative_path)


def read_repo_file_bytes(
    root_dir: str, relative_path: str, max_bytes: int
) -> tuple[str, bytes, bool]:
    """Read up to ``max_bytes`` (+1 to detect truncation).

    Status is one of: ``ok``, ``blocked``, ``missing``, ``not_file``, ``io_error``.
    """
    safe_relative = normalize_repo_relative_path(relative_path)
    if safe_relative is None:
        return "blocked", b"", False
    base_path = os.path.realpath(root_dir)
    fullpath = os.path.realpath(os.path.join(base_path, safe_relative))
    root_prefix = _root_prefix(base_path)
    if fullpath != base_path and not fullpath.startswith(root_prefix):
        return "blocked", b"", False
    if not os.path.exists(fullpath):
        return "missing", b"", False
    if not os.path.isfile(fullpath):
        return "not_file", b"", False
    try:
        with open(fullpath, "rb") as handle:
            raw = handle.read(max_bytes + 1)
    except OSError:
        return "io_error", b"", False
    truncated = len(raw) > max_bytes
    return "ok", raw[:max_bytes], truncated


def write_repo_file_bytes(root_dir: str, relative_path: str, payload: bytes) -> tuple[str, bytes | None]:
    """Write bytes. Status is ``ok``, ``blocked``, or ``io_error``."""
    safe_relative = normalize_repo_relative_path(relative_path)
    if safe_relative is None:
        return "blocked", None
    base_path = os.path.realpath(root_dir)
    fullpath = os.path.realpath(os.path.join(base_path, safe_relative))
    root_prefix = _root_prefix(base_path)
    if fullpath != base_path and not fullpath.startswith(root_prefix):
        return "blocked", None
    backup: bytes | None = None
    try:
        if os.path.isfile(fullpath):
            with open(fullpath, "rb") as handle:
                backup = handle.read(len(payload) + 1)
        parent_dir = os.path.dirname(fullpath)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        with open(fullpath, "wb") as handle:
            handle.write(payload)
    except OSError:
        return "io_error", backup
    return "ok", backup


def restore_or_remove_repo_file(root_dir: str, relative_path: str, backup: bytes | None) -> None:
    safe_relative = normalize_repo_relative_path(relative_path)
    if safe_relative is None:
        return
    base_path = os.path.realpath(root_dir)
    fullpath = os.path.realpath(os.path.join(base_path, safe_relative))
    root_prefix = _root_prefix(base_path)
    if fullpath != base_path and not fullpath.startswith(root_prefix):
        return
    try:
        if backup is not None:
            with open(fullpath, "wb") as handle:
                handle.write(backup)
        else:
            os.unlink(fullpath)
    except OSError:
        pass


def touch_repo_file(root_dir: str, relative_path: str) -> bool:
    safe_relative = normalize_repo_relative_path(relative_path)
    if safe_relative is None:
        return False
    base_path = os.path.realpath(root_dir)
    fullpath = os.path.realpath(os.path.join(base_path, safe_relative))
    root_prefix = _root_prefix(base_path)
    if fullpath != base_path and not fullpath.startswith(root_prefix):
        return False
    parent_dir = os.path.dirname(fullpath)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)
    open(fullpath, "a", encoding="utf-8").close()
    return True


def write_empty_repo_file(root_dir: str, relative_path: str) -> bool:
    safe_relative = normalize_repo_relative_path(relative_path)
    if safe_relative is None:
        return False
    base_path = os.path.realpath(root_dir)
    fullpath = os.path.realpath(os.path.join(base_path, safe_relative))
    root_prefix = _root_prefix(base_path)
    if fullpath != base_path and not fullpath.startswith(root_prefix):
        return False
    parent_dir = os.path.dirname(fullpath)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)
    with open(fullpath, "w", encoding="utf-8"):
        pass
    return True


def append_repo_text_line(root_dir: str, relative_path: str, text: str, *, append: bool) -> bool:
    safe_relative = normalize_repo_relative_path(relative_path)
    if safe_relative is None:
        return False
    base_path = os.path.realpath(root_dir)
    fullpath = os.path.realpath(os.path.join(base_path, safe_relative))
    root_prefix = _root_prefix(base_path)
    if fullpath != base_path and not fullpath.startswith(root_prefix):
        return False
    parent_dir = os.path.dirname(fullpath)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)
    mode = "a" if append else "w"
    with open(fullpath, mode, encoding="utf-8") as handle:
        handle.write(text)
        handle.write("\n")
    return True


def list_repo_path(root_dir: str, relative_path: str) -> tuple[str, str]:
    """Return (status, payload): status is ok|missing|blocked; payload is listing or message."""
    safe_relative = normalize_repo_relative_path(relative_path)
    if safe_relative is None:
        return "blocked", ""
    base_path = os.path.realpath(root_dir)
    fullpath = os.path.realpath(os.path.join(base_path, safe_relative))
    root_prefix = _root_prefix(base_path)
    if fullpath != base_path and not fullpath.startswith(root_prefix):
        return "blocked", ""
    if not os.path.exists(fullpath):
        return "missing", ""
    if os.path.isdir(fullpath):
        entries = sorted(
            (
                f"{name}/" if os.path.isdir(os.path.join(fullpath, name)) else name
                for name in os.listdir(fullpath)
            ),
            key=str.lower,
        )
        return "ok", "\n".join(entries)
    return "ok", os.path.basename(fullpath)


def mkdir_repo_path(root_dir: str, relative_path: str, *, parents: bool) -> tuple[str, str]:
    """Return (status, message). Status: ``ok``, ``blocked``, ``exists``, ``io_error``."""
    safe_relative = normalize_repo_relative_path(relative_path)
    if safe_relative is None:
        return "blocked", ""
    base_path = os.path.realpath(root_dir)
    fullpath = os.path.realpath(os.path.join(base_path, safe_relative))
    root_prefix = _root_prefix(base_path)
    if fullpath != base_path and not fullpath.startswith(root_prefix):
        return "blocked", ""
    if os.path.exists(fullpath):
        if parents:
            return "ok", ""
        return "exists", relative_path
    try:
        os.makedirs(fullpath, exist_ok=parents)
    except OSError:
        return "io_error", ""
    return "ok", ""
