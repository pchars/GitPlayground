"""Sandbox allowed-command policy (no shell)."""

from __future__ import annotations

import shlex

# Git subcommands learners must not invoke (network, hooks, config changes).
_BLOCKED_GIT_SUBCOMMANDS = frozenset(
    {
        "config",
        "daemon",
        "fetch",
        "pull",
        "push",
        "clone",
        "upload-pack",
        "receive-pack",
        "filter-branch",
        "replace",
        "remote",
        "submodule",
    }
)


SANDBOX_ALLOWED_COMMANDS_SUMMARY = (
    "git, ls, pwd, mkdir, touch, cat, head, tail, wc, cp, mv, rm, find, "
    "echo (вывод и запись в файл), type nul >, nano/edit, whoami, clear"
)


def relative_path_has_dotdot(relative_path: str) -> bool:
    norm = relative_path.strip().replace("\\", "/")
    return ".." in norm.split("/")


def normalize_repo_relative_path(relative_path: str) -> str | None:
    """Return a repo-relative path safe to join under a sandbox root, or None."""
    normalized = relative_path.strip().replace("\\", "/")
    if not normalized:
        return None
    if normalized.startswith(("/", "~")):
        return None
    if relative_path_has_dotdot(normalized):
        return None
    return normalized


def _git_tokens_allowed(tokens: list[str]) -> tuple[bool, str]:
    """Validate a git invocation: no -c/--config and no blocked subcommands."""
    idx = 1
    while idx < len(tokens):
        token = tokens[idx]
        if token in {"-c", "--config"}:
            return False, "git_config_injection"
        if token.startswith("-") and not token.startswith("--"):
            # short flags like -C are allowed only for directory-change teaching scenarios
            if token == "-C" and idx + 1 < len(tokens):
                idx += 2
                continue
            if token.startswith("-c"):
                return False, "git_config_injection"
            idx += 1
            continue
        if token.startswith("--"):
            if token in {"--config-env", "--config-env-var"}:
                return False, "git_config_injection"
            idx += 1
            continue
        sub = token.lower()
        if sub in _BLOCKED_GIT_SUBCOMMANDS:
            return False, f"git_subcommand_blocked:{sub}"
        return True, "git"
    return False, "git_missing_subcommand"


def _parse_optional_line_count(tokens: list[str], start: int) -> tuple[int | None, int]:
    if start >= len(tokens):
        return None, start
    token = tokens[start]
    if token == "-n" and start + 1 < len(tokens):
        try:
            return max(1, int(tokens[start + 1])), start + 2
        except ValueError:
            return None, start
    if token.startswith("-n") and len(token) > 2:
        try:
            return max(1, int(token[2:])), start + 1
        except ValueError:
            return None, start
    return None, start


def _validate_repo_path_token(path: str, *, reason_prefix: str) -> tuple[bool, str, dict]:
    if path.startswith("-"):
        return False, f"{reason_prefix}_flags_not_allowed", {}
    if relative_path_has_dotdot(path):
        return False, f"{reason_prefix}_path_dotdot", {}
    return True, "", {}


def parse_user_command(command: str) -> tuple[bool, str, dict]:
    try:
        tokens = shlex.split(command)
    except ValueError:
        return False, "syntax_error", {}
    if not tokens:
        return False, "empty_command", {}

    root = tokens[0]
    if root == "git":
        ok, reason = _git_tokens_allowed(tokens)
        if not ok:
            return False, reason, {}
        return True, "git", {"args": tokens}

    if root == "touch" and len(tokens) == 2:
        return True, "touch", {"path": tokens[1]}

    if root in {"nano", "edit"}:
        if len(tokens) != 2:
            return False, "nano_needs_path", {}
        ok, reason, _ = _validate_repo_path_token(tokens[1], reason_prefix="nano")
        if not ok:
            return False, reason, {}
        return True, "nano_open", {"path": tokens[1]}

    if root == "cat" and len(tokens) == 2:
        target = tokens[1]
        ok, reason, _ = _validate_repo_path_token(target, reason_prefix="cat")
        if not ok:
            return False, reason, {}
        return True, "cat_read", {"path": target}

    if root == "head":
        lines = 10
        idx = 1
        parsed_lines, idx = _parse_optional_line_count(tokens, idx)
        if parsed_lines is not None:
            lines = parsed_lines
        if idx >= len(tokens) or len(tokens) != idx + 1:
            return False, "head_needs_file", {}
        ok, reason, _ = _validate_repo_path_token(tokens[idx], reason_prefix="head")
        if not ok:
            return False, reason, {}
        return True, "head_read", {"path": tokens[idx], "lines": lines}

    if root == "tail":
        lines = 10
        idx = 1
        parsed_lines, idx = _parse_optional_line_count(tokens, idx)
        if parsed_lines is not None:
            lines = parsed_lines
        if idx >= len(tokens) or len(tokens) != idx + 1:
            return False, "tail_needs_file", {}
        ok, reason, _ = _validate_repo_path_token(tokens[idx], reason_prefix="tail")
        if not ok:
            return False, reason, {}
        return True, "tail_read", {"path": tokens[idx], "lines": lines}

    if root == "wc":
        lines_only = False
        idx = 1
        if idx < len(tokens) and tokens[idx] == "-l":
            lines_only = True
            idx += 1
        if idx >= len(tokens) or len(tokens) != idx + 1:
            return False, "wc_needs_file", {}
        ok, reason, _ = _validate_repo_path_token(tokens[idx], reason_prefix="wc")
        if not ok:
            return False, reason, {}
        return True, "wc_read", {"path": tokens[idx], "lines_only": lines_only}

    if root == "cp" and len(tokens) == 3:
        for path in (tokens[1], tokens[2]):
            ok, reason, _ = _validate_repo_path_token(path, reason_prefix="cp")
            if not ok:
                return False, reason, {}
        return True, "cp_file", {"src": tokens[1], "dst": tokens[2]}

    if root == "mv" and len(tokens) == 3:
        for path in (tokens[1], tokens[2]):
            ok, reason, _ = _validate_repo_path_token(path, reason_prefix="mv")
            if not ok:
                return False, reason, {}
        return True, "mv_file", {"src": tokens[1], "dst": tokens[2]}

    if root == "rm":
        targets: list[str] = []
        for token in tokens[1:]:
            if token == "-f":
                continue
            if token.startswith("-"):
                return False, "rm_flag_not_allowed", {}
            targets.append(token)
        if len(targets) != 1:
            return False, "rm_needs_one_path", {}
        ok, reason, _ = _validate_repo_path_token(targets[0], reason_prefix="rm")
        if not ok:
            return False, reason, {}
        return True, "rm_file", {"path": targets[0]}

    if root == "find":
        if len(tokens) == 1:
            path = "."
        elif len(tokens) == 2:
            path = tokens[1]
        else:
            return False, "find_too_many_args", {}
        if relative_path_has_dotdot(path):
            return False, "find_path_dotdot", {}
        return True, "find_paths", {"path": path}

    if root == "whoami" and len(tokens) == 1:
        return True, "whoami", {}

    if root == "clear" and len(tokens) == 1:
        return True, "clear", {}

    if root == "type" and len(tokens) == 4 and tokens[1].lower() == "nul" and tokens[2] == ">":
        return True, "type_nul_redirect", {"path": tokens[3]}

    if root == "pwd" and len(tokens) == 1:
        return True, "pwd", {}

    if root == "ls":
        targets = [t for t in tokens[1:] if not t.startswith("-")]
        if len(targets) > 1:
            return False, "ls_too_many_args", {}
        target = targets[0] if targets else "."
        if relative_path_has_dotdot(target):
            return False, "ls_path_dotdot", {}
        return True, "ls", {"path": target}

    if root == "mkdir":
        parents = False
        targets: list[str] = []
        for token in tokens[1:]:
            if token == "-p":
                parents = True
            elif token.startswith("-"):
                return False, "mkdir_flag_not_allowed", {}
            else:
                targets.append(token)
        if len(targets) != 1:
            return False, "mkdir_needs_one_path", {}
        if relative_path_has_dotdot(targets[0]):
            return False, "mkdir_path_dotdot", {}
        return True, "mkdir", {"path": targets[0], "parents": parents}

    if root == "echo":
        op_index = -1
        op_token = ""
        for idx, token in enumerate(tokens):
            if token in {">", ">>"}:
                op_index = idx
                op_token = token
                break
        if op_index > 1:
            if op_index + 1 >= len(tokens) or op_index + 2 != len(tokens):
                return False, "echo_invalid_redirect_target", {}
            text = " ".join(tokens[1:op_index]).strip()
            if not text:
                return False, "echo_empty_text", {}
            return True, "echo_redirect", {"text": text, "mode": op_token, "path": tokens[op_index + 1]}
        if len(tokens) > 1:
            return True, "echo_print", {"text": " ".join(tokens[1:])}
        return False, "echo_empty_text", {}

    return False, "command_not_allowed", {"command_root": root}
