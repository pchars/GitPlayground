import tempfile
from pathlib import Path

from django.test import SimpleTestCase

from apps.core.services.command_policy import normalize_repo_relative_path
from apps.core.services.repo_path_io import (
    list_repo_path,
    read_repo_file_bytes,
    resolve_trusted_path_under_root,
    write_repo_file_bytes,
)


class NormalizeRepoRelativePathTests(SimpleTestCase):
    def test_accepts_simple_relative_paths(self):
        self.assertEqual(normalize_repo_relative_path("notes/todo.txt"), "notes/todo.txt")
        self.assertEqual(normalize_repo_relative_path("."), ".")

    def test_rejects_traversal_and_absolute_paths(self):
        self.assertIsNone(normalize_repo_relative_path("../etc/passwd"))
        self.assertIsNone(normalize_repo_relative_path("/etc/passwd"))
        self.assertIsNone(normalize_repo_relative_path("~/secret"))


class ResolveTrustedPathTests(SimpleTestCase):
    def test_resolves_file_under_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "notes" / "todo.txt"
            target.parent.mkdir(parents=True)
            target.write_text("hi", encoding="utf-8")
            resolved = resolve_trusted_path_under_root(str(root), "notes/todo.txt")
            self.assertEqual(resolved, str(target.resolve()))

    def test_resolves_dot_as_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            resolved = resolve_trusted_path_under_root(tmp, ".")
            self.assertEqual(resolved, str(Path(tmp).resolve()))

    def test_read_blocks_dotdot_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            status, _payload, _truncated = read_repo_file_bytes(tmp, "../outside.txt", 1024)
            self.assertEqual(status, "blocked")

    def test_rejects_escape_via_realpath(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            outside = root.parent / "outside.txt"
            outside.write_text("no", encoding="utf-8")
            self.assertIsNone(resolve_trusted_path_under_root(str(root), f"../{outside.name}"))


class RepoPathIoTests(SimpleTestCase):
    def test_read_write_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            status, payload, truncated = read_repo_file_bytes(tmp, "new.txt", 1024)
            self.assertEqual(status, "missing")
            status, _backup = write_repo_file_bytes(tmp, "new.txt", b"hello")
            self.assertEqual(status, "ok")
            status, payload, truncated = read_repo_file_bytes(tmp, "new.txt", 1024)
            self.assertEqual(status, "ok")
            self.assertEqual(payload, b"hello")
            self.assertFalse(truncated)

    def test_list_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "a.txt").write_text("a", encoding="utf-8")
            Path(tmp, "sub").mkdir()
            status, listing = list_repo_path(tmp, ".")
            self.assertEqual(status, "ok")
            self.assertIn("a.txt", listing)
            self.assertIn("sub/", listing)
