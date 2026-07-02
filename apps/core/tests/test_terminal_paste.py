from django.test import SimpleTestCase

from apps.core.terminal_paste import apply_paste_to_command, sanitize_terminal_paste


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
        # Сценарий: пользователь напечатал "git init", в буфере "ls",
        # вставка должна дописать справа и получиться "git initls".
        self.assertEqual(apply_paste_to_command("git init", "ls"), "git initls")

    def test_paste_into_empty_buffer_equals_pasted_command(self):
        self.assertEqual(apply_paste_to_command("", "ls"), "ls")

    def test_paste_appends_sanitized_value(self):
        raw = "\x1b[1;32muser@gitplayground:~/repo$\x1b[0m ls\n"
        self.assertEqual(apply_paste_to_command("git init", raw), "git initls")
