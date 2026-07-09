"""Политика разрешённых команд песочницы (без shell)."""

from __future__ import annotations

import shlex

# Подкоманды git, которые ученик не должен вызывать (сеть, хуки, смена конфига).
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


def relative_path_has_dotdot(relative_path: str) -> bool:
    norm = relative_path.strip().replace("\\", "/")
    return ".." in norm.split("/")


def _git_tokens_allowed(tokens: list[str]) -> tuple[bool, str]:
    """Проверить git-вызов: без -c/--config и без заблокированных подкоманд."""
    idx = 1
    while idx < len(tokens):
        token = tokens[idx]
        if token in {"-c", "--config"}:
            return False, "git_config_injection"
        if token.startswith("-") and not token.startswith("--"):
            # короткие флаги вроде -C разрешены только для смены каталога в учебных сценариях
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

    if root == "cat" and len(tokens) == 2:
        target = tokens[1]
        if target.startswith("-"):
            return False, "cat_flags_not_allowed", {}
        if relative_path_has_dotdot(target):
            return False, "cat_path_dotdot", {}
        return True, "cat_read", {"path": target}

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
        if op_index <= 1:
            return False, "echo_missing_body_or_redirect", {}
        if op_index + 1 >= len(tokens) or op_index + 2 != len(tokens):
            return False, "echo_invalid_redirect_target", {}
        text = " ".join(tokens[1:op_index]).strip()
        if not text:
            return False, "echo_empty_text", {}
        return True, "echo_redirect", {"text": text, "mode": op_token, "path": tokens[op_index + 1]}

    return False, "command_not_allowed", {"command_root": root}
