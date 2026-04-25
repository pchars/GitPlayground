from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User
from django.test import Client, TestCase

from apps.achievements.models import Achievement, UserAchievement
from apps.core.services import can_open_task, get_or_create_active_session, run_command
from apps.progress.models import HintUsage, TaskCompletion, TaskRevisionProgress
from apps.sandbox.models import SandboxSession
from apps.tasks.models import Level, Task, TaskAsset, TaskRevision
from apps.users.models import UserProfile


class CoreFlowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="alice", password="password123")
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
        self.task2 = Task.objects.create(
            external_id="1.2",
            slug="task-1-2",
            title="Task 2",
            description="desc",
            level=self.level,
            order=2,
            points=10,
        )
        TaskAsset.objects.create(
            task=self.task1,
            asset_type=TaskAsset.AssetType.HINT,
            path="hints/hint1.txt",
            sort_order=1,
            content="Use git status.",
        )
        TaskRevision.objects.create(
            task=self.task1,
            version=1,
            is_active=True,
            objective="Complete task one objective.",
            steps=["Step one", "Step two"],
            expected_state="Expected repo state.",
            validator_notes="Validator checks repository status.",
        )
        UserProfile.objects.create(user=self.user, public_nickname="alice", total_points=20)

    def test_healthcheck(self):
        response = self.client.get("/healthz/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn(data["status"], {"ok", "degraded"})
        self.assertIn("checks", data)
        self.assertTrue(data["checks"]["database"])
        self.assertIn("X-Request-ID", response.headers)

    def test_request_id_propagates_from_header(self):
        response = self.client.get("/healthz/", HTTP_X_REQUEST_ID="rid-12345")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("X-Request-ID"), "rid-12345")

    def test_task_locking_order(self):
        self.assertTrue(can_open_task(self.user, self.task1))
        self.assertFalse(can_open_task(self.user, self.task2))
        TaskCompletion.objects.create(user=self.user, task=self.task1, points_awarded=5)
        self.assertTrue(can_open_task(self.user, self.task2))

    def test_sandbox_session_creation(self):
        session = get_or_create_active_session(self.user, self.task1)
        self.assertEqual(session.task_id, self.task1.id)
        self.assertTrue(session.repo_path)

    def test_playground_route_uses_correct_task_route_id(self):
        self.client.force_login(self.user)
        response = self.client.get("/playground/1_1/")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        self.assertIn('run: "/playground/1_1/run/"', content)
        self.assertNotIn("/playground/11_/", content)
        self.assertIn("Условие", content)
        self.assertIn("Complete task one objective.", content)
        self.assertNotIn("Sandbox path:", content)
        self.assertNotIn("Session:", content)
        self.assertIn('id="xterm-host"', content)
        self.assertNotIn('id="cmd-input"', content)

    def test_playground_api_endpoints_work(self):
        self.client.force_login(self.user)
        with self.assertLogs("apps.core.playground", level="INFO") as logs:
            run_res = self.client.post("/playground/1_1/run/", {"command": "git status"})
        self.assertEqual(run_res.status_code, 200)
        self.assertIn("ok", run_res.json())
        joined = "\n".join(logs.output)
        self.assertIn('"endpoint": "run"', joined)
        self.assertIn('"status_code": 200', joined)

        validate_res = self.client.post("/playground/1_1/validate/")
        self.assertEqual(validate_res.status_code, 200)
        self.assertIn("verdict", validate_res.json())
        self.assertIn("learning_content", validate_res.json())

    def test_playground_e2e_smoke_flow(self):
        self.client.force_login(self.user)
        page = self.client.get("/playground/1_1/")
        self.assertEqual(page.status_code, 200)

        run_res = self.client.post("/playground/1_1/run/", {"command": "git status"})
        self.assertEqual(run_res.status_code, 200)
        self.assertTrue(run_res.json()["ok"])

        hint_res = self.client.post("/playground/1_1/hint/", {"hint_index": 1})
        self.assertEqual(hint_res.status_code, 200)
        hint_payload = hint_res.json()
        self.assertTrue(hint_payload["ok"])
        self.assertEqual(hint_payload["points_spent"], 3)
        self.assertFalse(hint_payload.get("already_unlocked"))

        validate_res = self.client.post("/playground/1_1/validate/")
        self.assertEqual(validate_res.status_code, 200)
        self.assertTrue(validate_res.json()["ok"])

        reset_res = self.client.post("/playground/1_1/reset/")
        self.assertEqual(reset_res.status_code, 200)
        self.assertTrue(reset_res.json()["ok"])

    def test_playground_template_contains_local_help_command(self):
        self.client.force_login(self.user)
        response = self.client.get("/playground/1_1/")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        self.assertIn("/static/js/playground.js", content)
        js = (Path(settings.BASE_DIR) / "static" / "js" / "playground.js").read_text(encoding="utf-8")
        self.assertIn("GitPlayground help", js)
        self.assertIn("Локальная команда: help", js)

    def test_tasks_by_level_page_renders(self):
        self.client.force_login(self.user)
        response = self.client.get("/tasks/level/1/")
        self.assertEqual(response.status_code, 200)

    def test_playground_run_allows_safe_file_prep_commands(self):
        self.client.force_login(self.user)
        run_res = self.client.post("/playground/1_1/run/", {"command": 'echo "Hello, Git!" > hello.txt'})
        self.assertEqual(run_res.status_code, 200)
        payload = run_res.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["return_code"], 0)
        self.assertNotIn("checkpoint_state", payload)

    def test_playground_run_git_init_output_is_sanitized(self):
        self.client.force_login(self.user)
        self.client.get("/playground/1_1/")
        run_res = self.client.post("/playground/1_1/run/", {"command": "git init"})
        self.assertEqual(run_res.status_code, 200)
        payload = run_res.json()
        self.assertTrue(payload["ok"])
        out = (payload.get("output") or "").lower()
        self.assertNotIn(".sandboxes", out)
        self.assertNotIn("reinitialized", out)
        self.assertTrue(("репозитор" in out) or ("инициализ" in out))

    def test_init_repo_task_starts_without_preinitialized_git(self):
        init_task = Task.objects.create(
            external_id="1.0",
            slug="init_repo",
            title="Init Repo",
            description="init",
            level=self.level,
            order=3,
            points=1,
        )
        self.client.force_login(self.user)
        session = get_or_create_active_session(self.user, init_task)
        self.assertFalse((Path(session.repo_path) / ".git").exists())
        result = run_command(session, "git init")
        self.assertEqual(result.return_code, 0)
        out = (result.output or "").lower()
        self.assertIn("создан", out)
        self.assertNotIn("уже инициализирован", out)

    def test_init_repo_isolated_between_users(self):
        second_user = User.objects.create_user(username="bob", password="password123")
        init_task = Task.objects.create(
            external_id="1.3",
            slug="init_repo",
            title="Init Repo 2",
            description="init",
            level=self.level,
            order=3,
            points=1,
        )
        first_session = get_or_create_active_session(self.user, init_task)
        second_session = get_or_create_active_session(second_user, init_task)
        self.assertNotEqual(first_session.repo_path, second_session.repo_path)
        self.assertFalse((Path(first_session.repo_path) / ".git").exists())
        self.assertFalse((Path(second_session.repo_path) / ".git").exists())

    def test_playground_reset_endpoint_works(self):
        self.client.force_login(self.user)
        response = self.client.post("/playground/1_1/reset/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertIn("session_id", data)
        self.assertIn("status", data)

    def test_playground_hint_rejects_missing_without_spending_points(self):
        self.client.force_login(self.user)
        response = self.client.post("/playground/1_1/hint/", {"hint_index": 2})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["ok"])
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.total_points, 20)

    def test_playground_hint_first_costs_points(self):
        self.client.force_login(self.user)
        res = self.client.post("/playground/1_1/hint/", {"hint_index": 1})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["points_spent"], 3)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.total_points, 17)

    def test_playground_hint_repeat_unlock_does_not_charge_again(self):
        self.client.force_login(self.user)
        self.client.post("/playground/1_1/hint/", {"hint_index": 1})
        self.user.profile.refresh_from_db()
        pts_after_first = self.user.profile.total_points
        res = self.client.post("/playground/1_1/hint/", {"hint_index": 1})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["ok"])
        self.assertTrue(data.get("already_unlocked"))
        self.assertEqual(data["points_spent"], 0)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.total_points, pts_after_first)

    def test_playground_hint_rejects_when_balance_is_insufficient(self):
        self.client.force_login(self.user)
        self.user.profile.total_points = 0
        self.user.profile.save(update_fields=["total_points", "updated_at"])
        res = self.client.post("/playground/1_1/hint/", {"hint_index": 1})
        self.assertEqual(res.status_code, 400)
        self.assertFalse(res.json()["ok"])
        self.assertEqual(HintUsage.objects.filter(user=self.user, task=self.task1, hint_index=1).count(), 0)

    def test_tasks_page_shows_only_github_track(self):
        self.client.force_login(self.user)
        self.task1.platform = "github"
        self.task1.save(update_fields=["platform"])
        self.task2.platform = "gitlab"
        self.task2.save(update_fields=["platform"])
        tasks_page = self.client.get("/tasks/")
        self.assertEqual(tasks_page.status_code, 200)
        page_html = tasks_page.content.decode("utf-8")
        self.assertIn("Task 1", page_html)
        self.assertIn("GitHub", page_html)
        self.assertNotIn("GitLab", page_html)

    def test_playground_hint_requires_previous_hint(self):
        self.client.force_login(self.user)
        TaskAsset.objects.create(
            task=self.task1,
            asset_type=TaskAsset.AssetType.HINT,
            path="hints/hint2.txt",
            sort_order=2,
            content="Second hint.",
        )
        res = self.client.post("/playground/1_1/hint/", {"hint_index": 2})
        self.assertEqual(res.status_code, 400)
        self.assertIn("предыдущ", res.json().get("message", "").lower())
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.total_points, 20)
        self.assertEqual(HintUsage.objects.filter(user=self.user, task=self.task1).count(), 0)

    def test_playground_page_embeds_hint_ui_state(self):
        self.client.force_login(self.user)
        self.client.post("/playground/1_1/hint/", {"hint_index": 1})
        page = self.client.get("/playground/1_1/")
        self.assertEqual(page.status_code, 200)
        body = page.content.decode("utf-8")
        self.assertIn("hint-ui-state-data", body)
        self.assertIn("Use git status.", body)
        self.assertNotIn("Начать заново", body)

    def test_playground_hint_uses_ordered_position_not_sort_order_value(self):
        self.client.force_login(self.user)
        self.task1.assets.filter(asset_type=TaskAsset.AssetType.HINT).delete()
        TaskAsset.objects.create(
            task=self.task1,
            asset_type=TaskAsset.AssetType.HINT,
            path="hints/hint2.txt",
            sort_order=2,
            content="Second order but first unlocked hint.",
        )
        TaskAsset.objects.create(
            task=self.task1,
            asset_type=TaskAsset.AssetType.HINT,
            path="hints/hint4.txt",
            sort_order=4,
            content="Second unlocked hint.",
        )
        response = self.client.post("/playground/1_1/hint/", {"hint_index": 1})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["content"], "Second order but first unlocked hint.")

    def test_revision_progress_migrates_to_new_active_revision(self):
        self.client.force_login(self.user)
        self.client.get("/playground/1_1/")

        old_revision = self.task1.revisions.get(version=1)
        old_revision.is_active = False
        old_revision.save(update_fields=["is_active", "updated_at"])
        new_revision = TaskRevision.objects.create(
            task=self.task1,
            version=2,
            is_active=True,
            objective="Second revision objective.",
            steps=["S1"],
            expected_state="v2 state",
            validator_notes="v2 validator",
        )

        response = self.client.get("/playground/1_1/")
        self.assertEqual(response.status_code, 200)
        migrated = TaskRevisionProgress.objects.get(user=self.user, task=self.task1, is_current=True)
        self.assertEqual(migrated.revision_id, new_revision.id)
        self.assertIn("Second revision objective.", response.content.decode("utf-8"))

    def test_playground_fresh_query_creates_new_session_without_resetting_progress(self):
        self.client.force_login(self.user)
        self.client.get("/playground/1_1/")
        old_session = SandboxSession.objects.filter(user=self.user, task=self.task1).latest("id")
        self.client.get("/playground/1_1/?fresh=1")
        new_session = SandboxSession.objects.filter(user=self.user, task=self.task1).latest("id")
        self.assertNotEqual(old_session.id, new_session.id)
        old_session.refresh_from_db()
        self.assertEqual(old_session.status, SandboxSession.Status.STOPPED)

    def test_public_profile_renders_achievement_images(self):
        achievement = Achievement.objects.create(
            slug="first_commit",
            title="Первый коммит",
            description="Завершена первая задача.",
            icon_path="img/achievements/first_commit.png",
            points_bonus=5,
            threshold_tasks=1,
        )
        UserAchievement.objects.create(user=self.user, achievement=achievement)
        response = self.client.get(f"/profile/{self.user.username}/")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        self.assertIn("Первый коммит", content)
        self.assertIn("img/achievements/first_commit.png", content)
