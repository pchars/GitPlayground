import os
from unittest import mock

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import Client, TestCase

from apps.tasks.models import Level, Task, TaskRevision
from apps.users.models import UserProfile


class PlaygroundRateLimitTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client()
        self.user = User.objects.create_user(username="rluser", password="password123")
        self.level = Level.objects.create(number=1, title="L1", slug="l1", description="d")
        self.task1 = Task.objects.create(
            external_id="1.1",
            slug="task-1-1",
            title="Task 1",
            description="desc",
            level=self.level,
            order=1,
            points=5,
        )
        TaskRevision.objects.create(
            task=self.task1,
            version=1,
            is_active=True,
            objective="Objective",
            steps=[],
            expected_state="",
            validator_notes="",
        )
        UserProfile.objects.create(user=self.user, public_nickname="rluser", total_points=20)
        self.client.force_login(self.user)

    def test_run_endpoint_returns_429_when_over_limit(self):
        with mock.patch.dict(
            os.environ,
            {"PLAYGROUND_RL_MAX_RUN": "3", "PLAYGROUND_RL_WINDOW_SEC": "3600"},
            clear=False,
        ):
            for _ in range(3):
                r = self.client.post("/playground/1_1/run/", {"command": "git status"})
                self.assertEqual(r.status_code, 200, msg=r.content)
            r4 = self.client.post("/playground/1_1/run/", {"command": "git status"})
            self.assertEqual(r4.status_code, 429)
            self.assertIn("слишком", r4.json().get("message", "").lower())
