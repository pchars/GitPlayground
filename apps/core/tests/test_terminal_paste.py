from django.test import SimpleTestCase

from apps.core.terminal_paste import sanitize_terminal_paste


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
