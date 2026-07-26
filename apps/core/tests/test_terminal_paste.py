from django.test import SimpleTestCase

from apps.core.terminal_paste import apply_paste_to_command, sanitize_terminal_paste


def _sanitize_js_algorithm(text: str) -> str:
    """Mirror static/js/terminal_paste.js sanitizeTerminalPaste (keep in sync)."""
    import re

    prompt = "user@gitplayground:~/repo$ "
    ansi = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
    control = re.compile(r"[\x00-\x1f\x7f]")
    cleaned = ansi.sub("", text or "")
    cleaned = cleaned.replace(prompt, "")  # JS: split(PROMPT).join("")
    for line in cleaned.splitlines():
        stripped = control.sub("", line).strip()
        if stripped:
            return stripped
    return control.sub("", cleaned).strip()


class TerminalPasteSanitizeTests(SimpleTestCase):
    def test_strips_ansi_and_prompt_from_terminal_copy(self):
        raw = (
            "\x1b[1;32muser@gitplayground:~/repo$\x1b[0m git checkout main\n"
            "Switched to branch 'main'\n"
            "user@gitplayground:~/repo$\n"
        )
        self.assertEqual(sanitize_terminal_paste(raw), "git checkout main")

    def test_uses_first_non_empty_line_only(self):
        raw = "git init\n\ngit status\n"
        self.assertEqual(sanitize_terminal_paste(raw), "git init")

    def test_plain_command_is_unchanged(self):
        self.assertEqual(sanitize_terminal_paste("git status"), "git status")

    def test_empty_or_whitespace_returns_empty(self):
        self.assertEqual(sanitize_terminal_paste(""), "")
        self.assertEqual(sanitize_terminal_paste("   \n\n  "), "")


class TerminalPasteAppendTests(SimpleTestCase):
    def test_paste_appends_to_existing_command_without_overwriting(self):
        # Scenario: user typed "git init", clipboard contains "ls",
        # paste should append on the right producing "git initls".
        self.assertEqual(apply_paste_to_command("git init", "ls"), "git initls")

    def test_paste_into_empty_buffer_equals_pasted_command(self):
        self.assertEqual(apply_paste_to_command("", "ls"), "ls")

    def test_paste_appends_sanitized_value(self):
        raw = "\x1b[1;32muser@gitplayground:~/repo$\x1b[0m ls\n"
        self.assertEqual(apply_paste_to_command("git init", raw), "git initls")


class TerminalPasteParityTests(SimpleTestCase):
    """Python sanitize must match the JS algorithm mirror (and shared constants)."""

    CASES = (
        "",
        "   \n\n  ",
        "git status",
        "git init\n\ngit status\n",
        "user@gitplayground:~/repo$ ls\n",
        "\x1b[1;32muser@gitplayground:~/repo$\x1b[0m git checkout main\n"
        "Switched to branch 'main'\n"
        "user@gitplayground:~/repo$\n",
        "line1\r\nline2\r\n",
        "\x00git\x07 status\x1f",
    )

    def test_python_matches_js_algorithm_mirror(self):
        for raw in self.CASES:
            self.assertEqual(
                sanitize_terminal_paste(raw),
                _sanitize_js_algorithm(raw),
                msg=repr(raw),
            )

    def test_source_files_share_prompt_and_ansi_pattern(self):
        from pathlib import Path

        root = Path(__file__).resolve().parents[3]
        py = (root / "apps" / "core" / "terminal_paste.py").read_text(encoding="utf-8")
        js = (root / "static" / "js" / "terminal_paste.js").read_text(encoding="utf-8")
        self.assertIn("user@gitplayground:~/repo$ ", py)
        self.assertIn("user@gitplayground:~/repo$ ", js)
        self.assertIn(r"\x1b\[[0-9;]*[A-Za-z]", py)
        self.assertIn(r"\x1b\[[0-9;]*[A-Za-z]", js)
