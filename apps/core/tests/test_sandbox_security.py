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
