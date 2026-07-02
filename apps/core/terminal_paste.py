"""Sanitize text pasted into the playground terminal (mirrors static/js/terminal_paste.js)."""

from __future__ import annotations

import re

_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
_PROMPT = "user@gitplayground:~/repo$ "
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")


def sanitize_terminal_paste(text: str) -> str:
    """Return a single safe command line extracted from clipboard text."""
    cleaned = _ANSI_ESCAPE.sub("", text or "")
    cleaned = cleaned.replace(_PROMPT, "")
    for line in cleaned.splitlines():
        stripped = _CONTROL_CHARS.sub("", line).strip()
        if stripped:
            return stripped
    return _CONTROL_CHARS.sub("", cleaned).strip()


def apply_paste_to_command(command_buffer: str, pasted: str) -> str:
    """Return the command line after pasting clipboard text into the terminal.

    Mirrors ``applyPaste`` in ``static/js/playground.js``: the sanitized paste is
    appended to the right of whatever the user has already typed. It must never
    overwrite the existing input (e.g. buffer ``"git init"`` + paste ``"ls"`` must
    become ``"git initls"``, not ``"ls"``).
    """
    return (command_buffer or "") + sanitize_terminal_paste(pasted)
