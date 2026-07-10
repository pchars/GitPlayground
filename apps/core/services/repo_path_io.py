"""Trusted repo-relative file I/O (CodeQL py/path-injection safe).

Learner file paths are joined under a fixed sandbox root. CodeQL's
``py/path-injection`` query requires ``realpath(join(root, rel))``, a plain
``startswith(root_prefix)`` guard (no compound conditions), and the filesystem
call in the same function — parent dirs are resolved via ``join(base, dirname(rel))``.
"""

from __future__ import annotations

import os

from apps.core.services.command_policy import normalize_repo_relative_path

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


def _trusted_path_or_none(root_dir: str, relative_path: str) -> str | None:
    """Resolve a repo-relative path without touching the filesystem (tests/helpers)."""
    rel = normalize_repo_relative_path(relative_path)
    if rel is None:
        return None
    base_path = os.path.realpath(root_dir)
    root_prefix = _root_prefix(base_path)
    if rel == ".":
        return base_path
    fullpath = os.path.realpath(os.path.join(base_path, rel))
    if not fullpath.startswith(root_prefix):
        return None
    return fullpath


def _ensure_parent_dir(base_path: str, rel: str) -> bool:
    """Create parent directories for a repo-relative file path (CodeQL-safe)."""
    parent_rel = os.path.dirname(rel)
    if not parent_rel or parent_rel == ".":
        return True
    root_prefix = _root_prefix(base_path)
    parent_abs = os.path.realpath(os.path.join(base_path, parent_rel))
    if not parent_abs.startswith(root_prefix):
        return False
    try:
        os.makedirs(parent_abs, exist_ok=True)
    except OSError:
        return False
    return True


def resolve_trusted_path_under_root(root_dir: str, relative_path: str) -> str | None:
    """Return an absolute path under ``root_dir``, or None if rejected."""
    return _trusted_path_or_none(root_dir, relative_path)


def read_repo_file_bytes(
    root_dir: str, relative_path: str, max_bytes: int
) -> tuple[str, bytes, bool]:
    """Read up to ``max_bytes`` (+1 to detect truncation).

    Status is one of: ``ok``, ``blocked``, ``missing``, ``not_file``, ``io_error``.
    """
    rel = normalize_repo_relative_path(relative_path)
    if rel is None:
        return "blocked", b"", False
    base_path = os.path.realpath(root_dir)
    root_prefix = _root_prefix(base_path)
    fullpath = os.path.realpath(os.path.join(base_path, rel))
    if not fullpath.startswith(root_prefix):
        return "blocked", b"", False
    try:
        with open(fullpath, "rb") as handle:
            raw = handle.read(max_bytes + 1)
    except FileNotFoundError:
        return "missing", b"", False
    except IsADirectoryError:
        return "not_file", b"", False
    except OSError:
        return "io_error", b"", False
    truncated = len(raw) > max_bytes
    return "ok", raw[:max_bytes], truncated


def write_repo_file_bytes(root_dir: str, relative_path: str, payload: bytes) -> tuple[str, bytes | None]:
    """Write bytes. Status is ``ok``, ``blocked``, or ``io_error``."""
    rel = normalize_repo_relative_path(relative_path)
    if rel is None:
        return "blocked", None
    base_path = os.path.realpath(root_dir)
    root_prefix = _root_prefix(base_path)
    fullpath = os.path.realpath(os.path.join(base_path, rel))
    if not fullpath.startswith(root_prefix):
        return "blocked", None
    backup: bytes | None = None
    try:
        try:
            with open(fullpath, "rb") as handle:
                backup = handle.read(len(payload) + 1)
        except FileNotFoundError:
            backup = None
        if not _ensure_parent_dir(base_path, rel):
            return "blocked", backup
        with open(fullpath, "wb") as handle:
            handle.write(payload)
    except OSError:
        return "io_error", backup
    return "ok", backup


def restore_or_remove_repo_file(root_dir: str, relative_path: str, backup: bytes | None) -> None:
    rel = normalize_repo_relative_path(relative_path)
    if rel is None:
        return
    base_path = os.path.realpath(root_dir)
    root_prefix = _root_prefix(base_path)
    fullpath = os.path.realpath(os.path.join(base_path, rel))
    if not fullpath.startswith(root_prefix):
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
    rel = normalize_repo_relative_path(relative_path)
    if rel is None:
        return False
    base_path = os.path.realpath(root_dir)
    root_prefix = _root_prefix(base_path)
    fullpath = os.path.realpath(os.path.join(base_path, rel))
    if not fullpath.startswith(root_prefix):
        return False
    try:
        if not _ensure_parent_dir(base_path, rel):
            return False
        open(fullpath, "a", encoding="utf-8").close()
    except OSError:
        return False
    return True


def write_empty_repo_file(root_dir: str, relative_path: str) -> bool:
    rel = normalize_repo_relative_path(relative_path)
    if rel is None:
        return False
    base_path = os.path.realpath(root_dir)
    root_prefix = _root_prefix(base_path)
    fullpath = os.path.realpath(os.path.join(base_path, rel))
    if not fullpath.startswith(root_prefix):
        return False
    try:
        if not _ensure_parent_dir(base_path, rel):
            return False
        with open(fullpath, "w", encoding="utf-8"):
            pass
    except OSError:
        return False
    return True


def append_repo_text_line(root_dir: str, relative_path: str, text: str, *, append: bool) -> bool:
    rel = normalize_repo_relative_path(relative_path)
    if rel is None:
        return False
    base_path = os.path.realpath(root_dir)
    root_prefix = _root_prefix(base_path)
    fullpath = os.path.realpath(os.path.join(base_path, rel))
    if not fullpath.startswith(root_prefix):
        return False
    try:
        if not _ensure_parent_dir(base_path, rel):
            return False
        mode = "a" if append else "w"
        with open(fullpath, mode, encoding="utf-8") as handle:
            handle.write(text)
            handle.write("\n")
    except OSError:
        return False
    return True


def list_repo_path(root_dir: str, relative_path: str) -> tuple[str, str]:
    """Return (status, payload): status is ok|missing|blocked; payload is listing or message."""
    rel = normalize_repo_relative_path(relative_path)
    if rel is None:
        return "blocked", ""
    base_path = os.path.realpath(root_dir)
    root_prefix = _root_prefix(base_path)
    if rel == ".":
        fullpath = base_path
    else:
        fullpath = os.path.realpath(os.path.join(base_path, rel))
        if not fullpath.startswith(root_prefix):
            return "blocked", ""
    try:
        entries = sorted(os.listdir(fullpath), key=str.lower)
    except FileNotFoundError:
        return "missing", ""
    except NotADirectoryError:
        return "ok", os.path.basename(fullpath)
    except OSError:
        return "blocked", ""
    listing = "\n".join(
        f"{name}/" if os.path.isdir(os.path.join(fullpath, name)) else name for name in entries
    )
    return "ok", listing


def mkdir_repo_path(root_dir: str, relative_path: str, *, parents: bool) -> tuple[str, str]:
    """Return (status, message). Status: ``ok``, ``blocked``, ``exists``, ``io_error``."""
    rel = normalize_repo_relative_path(relative_path)
    if rel is None:
        return "blocked", ""
    base_path = os.path.realpath(root_dir)
    root_prefix = _root_prefix(base_path)
    if rel == ".":
        fullpath = base_path
    else:
        fullpath = os.path.realpath(os.path.join(base_path, rel))
        if not fullpath.startswith(root_prefix):
            return "blocked", ""
    try:
        os.makedirs(fullpath, exist_ok=parents)
    except FileExistsError:
        if parents:
            return "ok", ""
        return "exists", relative_path
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
    src_rel = normalize_repo_relative_path(src_path)
    dst_rel = normalize_repo_relative_path(dst_path)
    if src_rel is None or dst_rel is None:
        return "blocked", ""
    base_path = os.path.realpath(root_dir)
    root_prefix = _root_prefix(base_path)
    src_abs = os.path.realpath(os.path.join(base_path, src_rel))
    if not src_abs.startswith(root_prefix):
        return "blocked", ""
    dst_abs = os.path.realpath(os.path.join(base_path, dst_rel))
    if not dst_abs.startswith(root_prefix):
        return "blocked", ""
    try:
        with open(src_abs, "rb") as src_handle:
            payload = src_handle.read()
        if not _ensure_parent_dir(base_path, dst_rel):
            return "blocked", ""
        with open(dst_abs, "wb") as dst_handle:
            dst_handle.write(payload)
    except FileNotFoundError:
        return "missing", src_path
    except IsADirectoryError:
        return "not_file", src_path
    except OSError:
        return "io_error", ""
    return "ok", ""


def mv_repo_file(root_dir: str, src_path: str, dst_path: str) -> tuple[str, str]:
    if path_touches_git_metadata(src_path) or path_touches_git_metadata(dst_path):
        return "git_protected", ""
    src_rel = normalize_repo_relative_path(src_path)
    dst_rel = normalize_repo_relative_path(dst_path)
    if src_rel is None or dst_rel is None:
        return "blocked", ""
    base_path = os.path.realpath(root_dir)
    root_prefix = _root_prefix(base_path)
    src_abs = os.path.realpath(os.path.join(base_path, src_rel))
    if not src_abs.startswith(root_prefix):
        return "blocked", ""
    dst_abs = os.path.realpath(os.path.join(base_path, dst_rel))
    if not dst_abs.startswith(root_prefix):
        return "blocked", ""
    try:
        if not _ensure_parent_dir(base_path, dst_rel):
            return "blocked", ""
        os.replace(src_abs, dst_abs)
    except FileNotFoundError:
        return "missing", src_path
    except OSError:
        return "io_error", ""
    return "ok", ""


def rm_repo_path(root_dir: str, relative_path: str) -> tuple[str, str]:
    if path_touches_git_metadata(relative_path):
        return "git_protected", ""
    rel = normalize_repo_relative_path(relative_path)
    if rel is None:
        return "blocked", ""
    base_path = os.path.realpath(root_dir)
    root_prefix = _root_prefix(base_path)
    fullpath = os.path.realpath(os.path.join(base_path, rel))
    if not fullpath.startswith(root_prefix):
        return "blocked", ""
    try:
        os.unlink(fullpath)
    except FileNotFoundError:
        return "missing", relative_path
    except IsADirectoryError:
        return "is_dir", relative_path
    except OSError:
        return "io_error", ""
    return "ok", ""


def find_repo_paths(root_dir: str, relative_path: str) -> tuple[str, str]:
    rel = normalize_repo_relative_path(relative_path)
    if rel is None:
        return "blocked", ""
    base_path = os.path.realpath(root_dir)
    root_prefix = _root_prefix(base_path)
    if rel == ".":
        start_abs = base_path
    else:
        start_abs = os.path.realpath(os.path.join(base_path, rel))
        if not start_abs.startswith(root_prefix):
            return "blocked", ""
    entries: list[str] = []
    truncated = False
    try:
        for dirpath, dirnames, filenames in os.walk(start_abs):
            dirnames[:] = [name for name in dirnames if name != ".git"]
            rel_dir = os.path.relpath(dirpath, base_path).replace("\\", "/")
            if rel_dir == ".":
                rel_dir = ""
            for name in sorted(dirnames, key=str.lower):
                rel_entry = f"{rel_dir}/{name}/" if rel_dir else f"{name}/"
                entries.append(rel_entry)
                if len(entries) >= FIND_MAX_ENTRIES:
                    truncated = True
                    break
            if truncated:
                break
            for name in sorted(filenames, key=str.lower):
                rel_entry = f"{rel_dir}/{name}" if rel_dir else name
                full = os.path.realpath(os.path.join(dirpath, name))
                if full != base_path and not full.startswith(root_prefix):
                    continue
                entries.append(rel_entry)
                if len(entries) >= FIND_MAX_ENTRIES:
                    truncated = True
                    break
            if truncated:
                break
    except FileNotFoundError:
        return "missing", relative_path
    except NotADirectoryError:
        return "not_dir", relative_path
    except OSError:
        return "blocked", ""
    suffix = "\n[find: вывод обрезан по лимиту песочницы.]" if truncated else ""
    return "ok", "\n".join(entries) + suffix
