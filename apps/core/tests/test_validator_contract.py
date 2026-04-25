import tempfile
from datetime import timedelta
from pathlib import Path

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from apps.core.services import validate_task
from apps.progress.models import TaskAttempt
from apps.sandbox.models import SandboxSession
from apps.tasks.models import Level, Task, TaskAsset


class ValidatorContractTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="validator_user", password="password123")
        self.level = Level.objects.create(number=1, title="L1", slug="l1", description="d")
        self.task = Task.objects.create(
            external_id="7.7",
            slug="validator-task",
            title="Validator",
            description="d",
            level=self.level,
            order=1,
            points=1,
        )

    def _session(self, repo: Path) -> SandboxSession:
        return SandboxSession.objects.create(
            user=self.user,
            task=self.task,
            container_id="local-validator-test",
            repo_path=str(repo.resolve()),
            status=SandboxSession.Status.ACTIVE,
            expires_at=timezone.now() + timedelta(hours=1),
            timeout_seconds=30,
        )

    def test_local_validator_exit_zero_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "validator.py").write_text("raise SystemExit(0)\n", encoding="utf-8")
            session = self._session(repo)
            attempt = validate_task(self.user, self.task, session)
            self.assertEqual(attempt.verdict, TaskAttempt.Verdict.PASSED)

    def test_local_validator_exit_nonzero_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "validator.py").write_text("raise SystemExit(1)\n", encoding="utf-8")
            session = self._session(repo)
            attempt = validate_task(self.user, self.task, session)
            self.assertEqual(attempt.verdict, TaskAttempt.Verdict.FAILED)

    def test_asset_validator_is_deleted_after_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            TaskAsset.objects.create(
                task=self.task,
                asset_type=TaskAsset.AssetType.VALIDATOR,
                path="validator.py",
                content="raise SystemExit(0)\n",
                sort_order=1,
            )
            session = self._session(repo)
            attempt = validate_task(self.user, self.task, session)
            self.assertEqual(attempt.verdict, TaskAttempt.Verdict.PASSED)
            self.assertFalse((repo / "validator.py").exists())
