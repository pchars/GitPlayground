import threading
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.db import connection
from django.test import TransactionTestCase

from apps.core.services import get_or_create_active_session, validate_task
from apps.progress.models import TaskAttempt
from apps.sandbox.models import SandboxSession
from apps.tasks.models import Level, Task


class ValidateAttemptSerialTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.user = User.objects.create_user(username="parallel", password="pw")
        self.level = Level.objects.create(number=1, title="L1", slug="l1", description="d")
        self.task = Task.objects.create(
            external_id="9.9",
            slug="parallel-task",
            title="Parallel",
            description="d",
            level=self.level,
            order=1,
            points=3,
        )

    @patch("apps.core.services.learn_ops.subprocess.run")
    def test_parallel_validate_unique_attempt_numbers(self, mock_run):
        if connection.vendor == "sqlite":
            self.skipTest("SQLite cannot reliably run concurrent writes to the same tables from threads")
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
        session = get_or_create_active_session(self.user, self.task)
        self.assertIsInstance(session, SandboxSession)

        errors: list[BaseException] = []

        def worker():
            try:
                validate_task(self.user, self.task, session)
            except BaseException as exc:  # noqa: BLE001
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=60)
        self.assertFalse(errors, msg=errors)
        nos = list(
            TaskAttempt.objects.filter(user=self.user, task=self.task)
            .order_by("attempt_no")
            .values_list("attempt_no", flat=True)
        )
        self.assertEqual(len(nos), 8)
        self.assertEqual(sorted(nos), list(range(1, 9)))

    @patch("apps.core.services.learn_ops.subprocess.run")
    def test_sequential_validate_monotonic_attempt_numbers(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
        session = get_or_create_active_session(self.user, self.task)
        for _ in range(3):
            validate_task(self.user, self.task, session)
        nos = list(
            TaskAttempt.objects.filter(user=self.user, task=self.task)
            .order_by("attempt_no")
            .values_list("attempt_no", flat=True)
        )
        self.assertEqual(nos, [1, 2, 3])
