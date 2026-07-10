"""Trusted repo-relative file I/O (CodeQL py/path-injection safe).

User paths from the sandbox terminal are joined under a fixed workspace root.
CodeQL expects ``os.path.join(root, user_input)`` → ``os.path.realpath`` →
``startswith(root_prefix)`` in the same function that calls ``open()`` / ``os.*``.
"""

from __future__ import annotations

import os

FIND_MAX_ENTRIES = 500
HEAD_TAIL_MAX_LINES = 1000
SANDBOX_TEXT_FILE_READ_MAX_BYTES = 256 * 1024


def path_touches_git_metadata(relative_path: str) -> bool:
    """True when a repo-relative path targets the ``.git`` directory."""
    norm = relative_path.strip().replace("\\", "/").strip("/")
    if not norm or norm == ".":
        return False
    parts = norm.split("/")
    return parts[0] == ".git" or ".git" in parts


def _root_prefix(base_path: str) -> str:
    return base_path if base_path.endswith(os.sep) else f"{base_path}{os.sep}"


def _resolve_under_root(root_dir: str, relative_path: str) -> str | None:
    """Map learner-supplied repo-relative path to a trusted absolute path."""
    rel = relative_path.strip().replace("\\", "/")
    if not rel or rel.startswith(("/", "~")):
        return None
    base_path = os.path.realpath(root_dir)
    fullpath = os.path.realpath(os.path.join(base_path, rel))
    root_prefix = _root_prefix(base_path)
    if fullpath != base_path and not fullpath.startswith(root_prefix):
        return None
    return fullpath


def resolve_trusted_path_under_root(root_dir: str, relative_path: str) -> str | None:
    """Return an absolute path under ``root_dir``, or None if rejected."""
    return _resolve_under_root(root_dir, relative_path)


def read_repo_file_bytes(
    root_dir: str, relative_path: str, max_bytes: int
) -> tuple[str, bytes, bool]:
    """Read up to ``max_bytes`` (+1 to detect truncation).

    Status is one of: ``ok``, ``blocked``, ``missing``, ``not_file``, ``io_error``.
    """
    rel = relative_path.strip().replace("\\", "/")
    if not rel or rel.startswith(("/", "~")):
        return "blocked", b"", False
    base_path = os.path.realpath(root_dir)
    fullpath = os.path.realpath(os.path.join(base_path, rel))
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
    rel = relative_path.strip().replace("\\", "/")
    if not rel or rel.startswith(("/", "~")):
        return "blocked", None
    base_path = os.path.realpath(root_dir)
    fullpath = os.path.realpath(os.path.join(base_path, rel))
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
    rel = relative_path.strip().replace("\\", "/")
    if not rel or rel.startswith(("/", "~")):
        return
    base_path = os.path.realpath(root_dir)
    fullpath = os.path.realpath(os.path.join(base_path, rel))
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
    fullpath = _resolve_under_root(root_dir, relative_path)
    if fullpath is None:
        return False
    parent_dir = os.path.dirname(fullpath)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)
    open(fullpath, "a", encoding="utf-8").close()
    return True


def write_empty_repo_file(root_dir: str, relative_path: str) -> bool:
    fullpath = _resolve_under_root(root_dir, relative_path)
    if fullpath is None:
        return False
    parent_dir = os.path.dirname(fullpath)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)
    with open(fullpath, "w", encoding="utf-8"):
        pass
    return True


def append_repo_text_line(root_dir: str, relative_path: str, text: str, *, append: bool) -> bool:
    fullpath = _resolve_under_root(root_dir, relative_path)
    if fullpath is None:
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
    fullpath = _resolve_under_root(root_dir, relative_path)
    if fullpath is None:
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
    fullpath = _resolve_under_root(root_dir, relative_path)
    if fullpath is None:
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


def head_repo_file(root_dir: str, relative_path: str, *, lines: int) -> tuple[str, str]:
    """Return (status, payload). Status: ok|blocked|missing|not_file|io_error."""
    line_count = max(1, min(lines, HEAD_TAIL_MAX_LINES))
    status, raw, _ = read_repo_file_bytes(root_dir, relative_path, SANDBOX_TEXT_FILE_READ_MAX_BYTES)
    if status != "ok":
        return status, ""
    text = raw.decode("utf-8", errors="replace")
    selected = text.splitlines()[:line_count]
    return "ok", "\n".join(selected)


def tail_repo_file(root_dir: str, relative_path: str, *, lines: int) -> tuple[str, str]:
    line_count = max(1, min(lines, HEAD_TAIL_MAX_LINES))
    status, raw, _ = read_repo_file_bytes(root_dir, relative_path, SANDBOX_TEXT_FILE_READ_MAX_BYTES)
    if status != "ok":
        return status, ""
    text = raw.decode("utf-8", errors="replace")
    selected = text.splitlines()[-line_count:]
    return "ok", "\n".join(selected)


def wc_repo_file(root_dir: str, relative_path: str, *, lines_only: bool) -> tuple[str, str]:
    status, raw, _ = read_repo_file_bytes(
        root_dir, relative_path, SANDBOX_TEXT_FILE_READ_MAX_BYTES
    )
    if status != "ok":
        return status, ""
    text = raw.decode("utf-8", errors="replace")
    if lines_only:
        line_count = 0 if not text else len(text.splitlines())
        return "ok", str(line_count)
    return "ok", str(len(raw))


def cp_repo_file(root_dir: str, src_path: str, dst_path: str) -> tuple[str, str]:
    if path_touches_git_metadata(src_path) or path_touches_git_metadata(dst_path):
        return "git_protected", ""
    src_abs = _resolve_under_root(root_dir, src_path)
    dst_abs = _resolve_under_root(root_dir, dst_path)
    if src_abs is None or dst_abs is None:
        return "blocked", ""
    if not os.path.isfile(src_abs):
        if not os.path.exists(src_abs):
            return "missing", src_path
        return "not_file", src_path
    try:
        parent_dir = os.path.dirname(dst_abs)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        with open(src_abs, "rb") as src_handle:
            payload = src_handle.read()
        with open(dst_abs, "wb") as dst_handle:
            dst_handle.write(payload)
    except OSError:
        return "io_error", ""
    return "ok", ""


def mv_repo_file(root_dir: str, src_path: str, dst_path: str) -> tuple[str, str]:
    if path_touches_git_metadata(src_path) or path_touches_git_metadata(dst_path):
        return "git_protected", ""
    src_abs = _resolve_under_root(root_dir, src_path)
    dst_abs = _resolve_under_root(root_dir, dst_path)
    if src_abs is None or dst_abs is None:
        return "blocked", ""
    if not os.path.exists(src_abs):
        return "missing", src_path
    try:
        parent_dir = os.path.dirname(dst_abs)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        os.replace(src_abs, dst_abs)
    except OSError:
        return "io_error", ""
    return "ok", ""


def rm_repo_path(root_dir: str, relative_path: str) -> tuple[str, str]:
    if path_touches_git_metadata(relative_path):
        return "git_protected", ""
    fullpath = _resolve_under_root(root_dir, relative_path)
    if fullpath is None:
        return "blocked", ""
    if not os.path.exists(fullpath):
        return "missing", relative_path
    if os.path.isdir(fullpath):
        return "is_dir", relative_path
    try:
        os.unlink(fullpath)
    except OSError:
        return "io_error", ""
    return "ok", ""


def find_repo_paths(root_dir: str, relative_path: str) -> tuple[str, str]:
    start_abs = _resolve_under_root(root_dir, relative_path)
    if start_abs is None:
        return "blocked", ""
    if not os.path.exists(start_abs):
        return "missing", relative_path
    if not os.path.isdir(start_abs):
        return "not_dir", relative_path
    base_path = os.path.realpath(root_dir)
    root_prefix = _root_prefix(base_path)
    entries: list[str] = []
    truncated = False
    for dirpath, dirnames, filenames in os.walk(start_abs):
        dirnames[:] = [name for name in dirnames if name != ".git"]
        rel_dir = os.path.relpath(dirpath, base_path).replace("\\", "/")
        if rel_dir == ".":
            rel_dir = ""
        for name in sorted(dirnames, key=str.lower):
            rel = f"{rel_dir}/{name}/" if rel_dir else f"{name}/"
            entries.append(rel)
            if len(entries) >= FIND_MAX_ENTRIES:
                truncated = True
                break
        if truncated:
            break
        for name in sorted(filenames, key=str.lower):
            rel = f"{rel_dir}/{name}" if rel_dir else name
            full = os.path.realpath(os.path.join(dirpath, name))
            if full != base_path and not full.startswith(root_prefix):
                continue
            entries.append(rel)
            if len(entries) >= FIND_MAX_ENTRIES:
                truncated = True
                break
        if truncated:
            break
    suffix = "\n[find: вывод обрезан по лимиту песочницы.]" if truncated else ""
    return "ok", "\n".join(entries) + suffix
