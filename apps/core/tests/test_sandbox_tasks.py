from pathlib import Path
from uuid import uuid4

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from apps.core.services.sandbox_ops import SANDBOX_ROOT, _ensure_sandbox_root
from apps.sandbox.models import SandboxSession
from apps.sandbox.tasks import cleanup_expired_sandboxes
from apps.tasks.models import Level, Task


class SandboxCleanupTaskTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="cleaner", password="password123")
        self.level = Level.objects.create(number=1, title="L1", slug="l1", description="d")
        self.task = Task.objects.create(
            external_id="9.9",
            slug="cleanup-task",
            title="Cleanup",
            description="d",
            level=self.level,
            order=1,
            points=1,
        )

    def test_cleanup_expired_sandboxes_removes_workspace_and_marks_expired(self):
        _ensure_sandbox_root()
        workspace = SANDBOX_ROOT / f"gp_cleanup_test_{uuid4().hex}"
        workspace.mkdir(parents=True)
        marker = workspace / "marker.txt"
        marker.write_text("x", encoding="utf-8")
        past = timezone.now() - timezone.timedelta(hours=1)
        session = SandboxSession.objects.create(
            user=self.user,
            task=self.task,
            container_id="local-test-cleanup-1",
            repo_path=str(workspace.resolve()),
            status=SandboxSession.Status.ACTIVE,
            expires_at=past,
        )
        cleaned = cleanup_expired_sandboxes()
        self.assertGreaterEqual(cleaned, 1, msg="expected at least one expired active session cleaned")
        session.refresh_from_db()
        self.assertEqual(session.status, SandboxSession.Status.EXPIRED)
        self.assertFalse(marker.exists())
