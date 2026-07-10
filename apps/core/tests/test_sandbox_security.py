import io
import tempfile
import zipfile
from pathlib import Path

from django.test import SimpleTestCase

from apps.core.services.command_policy import parse_user_command
from apps.core.services.workspace_seed import safe_extract_zip


class CommandPolicySecurityTests(SimpleTestCase):
    def test_blocks_git_config_subcommand(self):
        allowed, reason, _ = parse_user_command("git config user.name evil")
        self.assertFalse(allowed)
        self.assertIn("config", reason)

    def test_blocks_git_config_injection_flag(self):
        allowed, reason, _ = parse_user_command("git -c core.hooksPath=/tmp/evil status")
        self.assertFalse(allowed)
        self.assertEqual(reason, "git_config_injection")

    def test_blocks_git_push(self):
        allowed, reason, _ = parse_user_command("git push origin main")
        self.assertFalse(allowed)
        self.assertIn("push", reason)

    def test_allows_git_status(self):
        allowed, reason, data = parse_user_command("git status")
        self.assertTrue(allowed)
        self.assertEqual(reason, "git")
        self.assertEqual(data["args"], ["git", "status"])

    def test_allows_pwd(self):
        allowed, reason, data = parse_user_command("pwd")
        self.assertTrue(allowed)
        self.assertEqual(reason, "pwd")
        self.assertEqual(data, {})

    def test_allows_ls_with_optional_flags(self):
        allowed, reason, data = parse_user_command("ls -la notes")
        self.assertTrue(allowed)
        self.assertEqual(reason, "ls")
        self.assertEqual(data["path"], "notes")

    def test_blocks_ls_path_traversal(self):
        allowed, reason, _ = parse_user_command("ls ../escape")
        self.assertFalse(allowed)
        self.assertEqual(reason, "ls_path_dotdot")

    def test_allows_mkdir_with_parents_flag(self):
        allowed, reason, data = parse_user_command("mkdir -p nested/dir")
        self.assertTrue(allowed)
        self.assertEqual(reason, "mkdir")
        self.assertEqual(data, {"path": "nested/dir", "parents": True})

    def test_blocks_mkdir_multiple_paths(self):
        allowed, reason, _ = parse_user_command("mkdir a b")
        self.assertFalse(allowed)
        self.assertEqual(reason, "mkdir_needs_one_path")

    def test_allows_echo_redirect_append(self):
        allowed, reason, data = parse_user_command('echo "line" >> file.txt')
        self.assertTrue(allowed)
        self.assertEqual(reason, "echo_redirect")
        self.assertEqual(data["text"], "line")
        self.assertEqual(data["mode"], ">>")
        self.assertEqual(data["path"], "file.txt")

    def test_blocks_unknown_shell_verb(self):
        allowed, reason, data = parse_user_command("rm -rf .")
        self.assertFalse(allowed)
        self.assertEqual(reason, "command_not_allowed")
        self.assertEqual(data["command_root"], "rm")


class SafeZipExtractTests(SimpleTestCase):
    def test_rejects_zip_slip_member(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "workspace"
            dest.mkdir()
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w") as zf:
                zf.writestr("../evil.txt", "pwn")
            buf.seek(0)
            with zipfile.ZipFile(buf, "r") as archive:
                with self.assertRaises(ValueError):
                    safe_extract_zip(archive, dest)
            self.assertFalse((dest.parent / "evil.txt").exists())
