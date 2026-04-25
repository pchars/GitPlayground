import tempfile
from pathlib import Path

from django.test import TestCase

from apps.core.services.sandbox_ops import (
    SANDBOX_ROOT,
    _ensure_sandbox_root,
    rmtree_sandbox_workspace_if_safe,
    validated_sandbox_workspace,
)


class SandboxPathGuardTests(TestCase):
    def test_rejects_path_outside_sandbox_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            evil = Path(tmp) / "outside"
            evil.mkdir()
            marker = evil / "keep.txt"
            marker.write_text("x", encoding="utf-8")
            with self.assertRaises(ValueError):
                validated_sandbox_workspace(str(evil.resolve()))

    def test_rmtree_skips_escape_attempt(self):
        with tempfile.TemporaryDirectory() as tmp:
            evil = Path(tmp) / "escape"
            evil.mkdir()
            marker = evil / "keep.txt"
            marker.write_text("x", encoding="utf-8")
            ok = rmtree_sandbox_workspace_if_safe(str(evil.resolve()))
            self.assertFalse(ok)
            self.assertTrue(marker.exists())

    def test_rmtree_removes_workspace_under_root(self):
        _ensure_sandbox_root()
        workspace = SANDBOX_ROOT / "gp_path_guard_test_workspace"
        workspace.mkdir(parents=True, exist_ok=True)
        marker = workspace / "m.txt"
        marker.write_text("y", encoding="utf-8")
        self.assertTrue(rmtree_sandbox_workspace_if_safe(str(workspace.resolve())))
        self.assertFalse(marker.exists())
