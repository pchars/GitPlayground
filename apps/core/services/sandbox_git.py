"""Deterministic git environment for the sandbox."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from django.conf import settings

SANDBOX_ROOT = Path(settings.BASE_DIR) / ".sandboxes"
RUNNING_TESTS = "test" in sys.argv

SANDBOX_GIT_CONFIG = SANDBOX_ROOT / "_gitconfig"
SANDBOX_NO_HOOKS_DIR = SANDBOX_ROOT / "_no_hooks"
SANDBOX_GIT_USER_NAME = "GitPlayground Learner"
SANDBOX_GIT_USER_EMAIL = "learner@gitplayground.local"
_GIT_CONFIG_TEMPLATE = (
    "[init]\n"
    "\tdefaultBranch = main\n"
    "[user]\n"
    "\tname = {name}\n"
    "\temail = {email}\n"
    "[safe]\n"
    "\tdirectory = *\n"
    "[core]\n"
    "\thooksPath = {hooks_path}\n"
    "[commit]\n"
    "\tgpgsign = false\n"
    "[tag]\n"
    "\tgpgsign = false\n"
)


def ensure_sandbox_root() -> None:
    SANDBOX_ROOT.mkdir(exist_ok=True)


def ensure_no_hooks_dir() -> Path:
    """Empty directory used as core.hooksPath so no hook scripts can run."""
    ensure_sandbox_root()
    try:
        SANDBOX_NO_HOOKS_DIR.mkdir(exist_ok=True)
    except OSError:
        pass
    return SANDBOX_NO_HOOKS_DIR


def ensure_git_config() -> Path:
    ensure_sandbox_root()
    hooks_path = str(ensure_no_hooks_dir().resolve()).replace("\\", "/")
    expected = _GIT_CONFIG_TEMPLATE.format(
        name=SANDBOX_GIT_USER_NAME,
        email=SANDBOX_GIT_USER_EMAIL,
        hooks_path=hooks_path,
    )
    try:
        if not SANDBOX_GIT_CONFIG.exists() or SANDBOX_GIT_CONFIG.read_text(encoding="utf-8") != expected:
            SANDBOX_GIT_CONFIG.write_text(expected, encoding="utf-8")
    except OSError:
        pass
    return SANDBOX_GIT_CONFIG


def git_env() -> dict[str, str]:
    env = os.environ.copy()
    env["GIT_CONFIG_GLOBAL"] = str(ensure_git_config())
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_CEILING_DIRECTORIES"] = str(SANDBOX_ROOT.resolve())
    return env
