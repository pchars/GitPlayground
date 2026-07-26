import io
import tempfile
import zipfile
from pathlib import Path

from django.test import SimpleTestCase

from apps.core.services.command_policy import parse_user_command
from apps.core.services.workspace_seed import safe_extract_zip


class CommandPolicySecurityTests(SimpleTestCase):
    def test_blocks_all_blocked_git_subcommands(self):
        from apps.core.services.command_policy import _BLOCKED_GIT_SUBCOMMANDS

        for sub in sorted(_BLOCKED_GIT_SUBCOMMANDS):
            allowed, reason, _ = parse_user_command(f"git {sub}")
            self.assertFalse(allowed, msg=sub)
            self.assertEqual(reason, f"git_subcommand_blocked:{sub}", msg=sub)

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
        allowed, reason, data = parse_user_command("bash -c ls")
        self.assertFalse(allowed)
        self.assertEqual(reason, "command_not_allowed")
        self.assertEqual(data["command_root"], "bash")

    def test_allows_nano_and_edit_alias(self):
        for cmd in ("nano notes.txt", "edit notes.txt"):
            allowed, reason, data = parse_user_command(cmd)
            self.assertTrue(allowed, msg=cmd)
            self.assertEqual(reason, "nano_open")
            self.assertEqual(data["path"], "notes.txt")

    def test_allows_echo_without_redirect(self):
        allowed, reason, data = parse_user_command("echo hello world")
        self.assertTrue(allowed)
        self.assertEqual(reason, "echo_print")
        self.assertEqual(data["text"], "hello world")

    def test_allows_head_tail_wc(self):
        allowed, reason, data = parse_user_command("head -n 3 hello.txt")
        self.assertTrue(allowed)
        self.assertEqual(reason, "head_read")
        self.assertEqual(data, {"path": "hello.txt", "lines": 3})

        allowed, reason, data = parse_user_command("tail hello.txt")
        self.assertTrue(allowed)
        self.assertEqual(reason, "tail_read")
        self.assertEqual(data, {"path": "hello.txt", "lines": 10})

        allowed, reason, data = parse_user_command("wc -l hello.txt")
        self.assertTrue(allowed)
        self.assertEqual(reason, "wc_read")
        self.assertEqual(data, {"path": "hello.txt", "lines_only": True})

    def test_allows_cp_mv_rm_find(self):
        allowed, reason, data = parse_user_command("cp a.txt b.txt")
        self.assertTrue(allowed)
        self.assertEqual(reason, "cp_file")

        allowed, reason, data = parse_user_command("mv a.txt b.txt")
        self.assertTrue(allowed)
        self.assertEqual(reason, "mv_file")

        allowed, reason, data = parse_user_command("rm -f temp.txt")
        self.assertTrue(allowed)
        self.assertEqual(reason, "rm_file")
        self.assertEqual(data["path"], "temp.txt")

        allowed, reason, data = parse_user_command("find .")
        self.assertTrue(allowed)
        self.assertEqual(reason, "find_paths")

    def test_blocks_rm_recursive_flag(self):
        allowed, reason, _ = parse_user_command("rm -r folder")
        self.assertFalse(allowed)
        self.assertEqual(reason, "rm_flag_not_allowed")

    def test_allows_whoami_and_clear(self):
        self.assertTrue(parse_user_command("whoami")[0])
        self.assertTrue(parse_user_command("clear")[0])

    def test_blocks_git_workdir_escape_flags(self):
        for cmd in (
            "git -C /tmp status",
            "git --git-dir=/evil status",
            "git --work-tree=/tmp status",
            "git --namespace=evil status",
        ):
            allowed, reason, _ = parse_user_command(cmd)
            self.assertFalse(allowed, msg=cmd)
            self.assertEqual(reason, "git_workdir_flag_blocked", msg=cmd)


class GitMetadataWriteProtectionTests(SimpleTestCase):
    def test_write_paths_reject_dot_git(self):
        from apps.core.services.repo_path_io import (
            append_repo_text_line,
            mkdir_repo_path,
            touch_repo_file,
            write_empty_repo_file,
            write_repo_file_bytes,
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".git").mkdir()
            status, _ = write_repo_file_bytes(tmp, ".git/hooks/pre-commit", b"evil")
            self.assertEqual(status, "git_protected")
            self.assertFalse(touch_repo_file(tmp, ".git/config"))
            self.assertFalse(write_empty_repo_file(tmp, ".git/HEAD"))
            self.assertFalse(append_repo_text_line(tmp, ".git/hooks/x", "x", append=False))
            status, _ = mkdir_repo_path(tmp, ".git/hooks", parents=True)
            self.assertEqual(status, "git_protected")
            self.assertFalse((root / ".git" / "hooks" / "pre-commit").exists())

    def test_git_env_disables_hooks(self):
        from apps.core.services.sandbox_git import SANDBOX_NO_HOOKS_DIR, ensure_git_config, git_env

        env = git_env()
        config_path = Path(env["GIT_CONFIG_GLOBAL"])
        text = config_path.read_text(encoding="utf-8")
        hooks = str(SANDBOX_NO_HOOKS_DIR.resolve()).replace("\\", "/")
        self.assertIn(f"hooksPath = {hooks}", text)
        self.assertEqual(config_path, ensure_git_config())


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
